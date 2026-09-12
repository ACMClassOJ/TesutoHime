"""Read and clean up the submission cgroup created by runner.c.

Python never creates the group or moves a process into it. The runner's host
setup mode creates it; the sandboxed runner joins only its submission child.
"""

from errno import EBUSY
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4


class RunCgroup:
    # runner.c opens this membership handle before entering nsjail's namespaces.
    procs_fd = 3

    def __init__(self, parent: Path):
        self.parent = parent
        self.path = parent / f"acmoj-{uuid4()}"

    def __enter__(self):
        return self

    def launcher(self, runner: str, memory_max: int, pids_max: int) -> list[str]:
        return [runner, '--prepare-cgroup', str(self.parent), self.path.name,
                str(memory_max), str(pids_max), '--']

    @property
    def memory_peak(self) -> int:
        if not self.path.exists():
            # The trusted launcher failed before starting the submission.
            return 0
        return int((self.path / "memory.peak").read_text())

    @property
    def oom_killed(self) -> bool:
        if not self.path.exists():
            return False
        events = dict(line.split() for line in
                      (self.path / "memory.events").read_text().splitlines())
        return int(events["oom_kill"]) > 0

    def __exit__(self, *_args):
        if not self.path.exists():
            return
        # Also handles failed setup on kernels without memory.peak/cgroup.kill:
        # an empty group can be removed without using either interface.
        try:
            self.path.rmdir()
            return
        except OSError as e:
            if e.errno != EBUSY:
                raise
        (self.path / "cgroup.kill").write_text("1")
        deadline = monotonic() + 5
        while "populated 1" in (self.path / "cgroup.events").read_text():
            if monotonic() >= deadline:
                raise RuntimeError(f"Processes remain in {self.path} after cgroup.kill")
            sleep(0.01)
        # The runner creates one leaf. No cgroup directory is exposed to the
        # submission, and every cgroup descriptor is closed before its exec.
        self.path.rmdir()
