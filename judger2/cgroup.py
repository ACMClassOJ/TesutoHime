"""Per-invocation cgroup v2 parent for nsjail runs.

The configured delegation must provide the memory and pids controllers.
nsjail creates its limited child underneath this directory. Keeping a parent
lets us read the memory peak and OOM events even after nsjail removes its child.
"""

from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4


class RunCgroup:
    def __init__(self, parent: Path):
        self.parent = parent
        self.path = parent / f"acmoj-{uuid4()}"

    def __enter__(self):
        # Idempotent and limited to the trusted, delegated subtree. A populated
        # parent (misconfigured supervisor) fails here instead of dropping limits.
        (self.parent / "cgroup.subtree_control").write_text("+memory +pids")
        self.path.mkdir(mode=0o700)
        try:
            controllers = (self.path / "cgroup.controllers").read_text().split()
            if not {"memory", "pids"}.issubset(controllers):
                raise RuntimeError("Sandbox cgroups require delegated memory and pids controllers")
            if not (self.path / "cgroup.kill").exists():
                raise RuntimeError("Sandbox cleanup requires cgroup.kill (Linux 5.14+)")
            if not (self.path / "memory.peak").exists():
                raise RuntimeError("Sandbox memory accounting requires memory.peak (Linux 5.19+)")
            (self.path / "cgroup.subtree_control").write_text("+memory +pids")
        except BaseException:
            self.path.rmdir()
            raise
        return self

    @property
    def memory_peak(self) -> int:
        return int((self.path / "memory.peak").read_text())

    @property
    def oom_killed(self) -> bool:
        events = dict(line.split() for line in
                      (self.path / "memory.events").read_text().splitlines())
        return int(events["oom_kill"]) > 0

    def kill(self):
        (self.path / "cgroup.kill").write_text("1")

    def __exit__(self, *_args):
        self.kill()
        deadline = monotonic() + 5
        while "populated 1" in (self.path / "cgroup.events").read_text():
            if monotonic() >= deadline:
                raise RuntimeError(f"Processes remain in {self.path} after cgroup.kill")
            sleep(0.01)
        # Only nsjail can create children here; this directory is not mounted
        # into the sandbox and belongs to the service UID, not the worker UID.
        for child in sorted(self.path.rglob("*"), reverse=True):
            if child.is_dir():
                child.rmdir()
        self.path.rmdir()
