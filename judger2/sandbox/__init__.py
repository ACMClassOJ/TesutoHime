__all__ = 'run_with_limits', 'chown_back'

from asyncio import CancelledError, create_subprocess_exec, create_task, shield, wait_for
from dataclasses import asdict, dataclass, field
from logging import getLogger
from math import ceil
from os import (P_PID, WEXITED, WEXITSTATUS, WIFEXITED, WIFSIGNALED, WNOWAIT,
                WTERMSIG, getuid, kill, strerror, waitid, waitpid)
from pathlib import PosixPath
from posixpath import normpath
from shlex import quote
from shutil import which
from signal import SIGKILL, strsignal
from subprocess import DEVNULL, PIPE, Popen
from sys import platform
from time import time
from typing import (IO, Any, Callable, Coroutine, List, Optional, Sequence,
                    Union)

from typing_extensions import Literal

from commons.task_typing import ResourceUsage, RunResult
from commons.util import asyncrun
from judger2.config import config
from judger2.cgroup import RunCgroup
from judger2.util import TempDir, format_args

logger = getLogger(__name__)


if platform != 'linux':
    logger.critical('This judger runs only on Linux systems, but your system seems to be %(platform)s.', { 'platform': platform }, 'sandbox:invalidplatform')
    exit(2)


nsjail = PosixPath(__file__).with_name('nsjail')
nsjail_wrapper = PosixPath(__file__).with_name('stdenv') / 'bin' / 'nsjail-wrapper'
if not nsjail.exists() or not nsjail_wrapper.exists():
    raise Exception('nsjail executable not found')
nsjail = str(nsjail)
nsjail_wrapper = str(nsjail_wrapper)

bindmount_ro_base = ['/dev/urandom']
bindmount_rw_base = ['/dev/null', '/dev/zero']
worker_uid_inside = 65534
worker_uid_maps = [
    f'0:{getuid()}:1', # map current user to 0
    f'{worker_uid_inside}:{config.worker_uid}:1', # map worker
]

def waitstatus_to_exitcode (status: int):
    if WIFEXITED(status):
        return WEXITSTATUS(status)
    if WIFSIGNALED(status):
        return -WTERMSIG(status)
    raise ValueError(f'Invalid waitstatus {status}')

@dataclass
class NsjailArgs:
    # where to chroot to.
    chroot: str
    # the program working dir.
    cwd: str
    # time limit (str, but in secs) for the runner.
    time_limit: str
    # cpu time limit (secs) RLIMIT_CPU.
    rlimit_cpu: str = '600'
    # Memory is limited by the submission cgroup.
    rlimit_as: str = 'inf'
    # number of open file descriptors, defaults to 32 by nsjail which is too low.
    rlimit_nofile: str = '1024'

    # readonly mount points.
    bindmount_ro: Union[List[str], bool] = False
    # R/W mount points.
    bindmount: Union[List[str], bool] = False

    # maximum size in megabytes of files that the process may create.
    rlimit_fsize: str = 'inf'
    # Trusted runner handles, closed before executing the submission.
    pass_fd: List[str] = field(default_factory=list)

    # whether to enable network access in the container.
    disable_clone_newnet: bool = False

    mode: str = 'o'
    really_quiet: bool = True
    max_cpus: str = '1'
    rlimit_stack: str = 'inf'
    # capabilities(7) to grant to the program.
    cap: str = 'CAP_SETUID'
    uid_mapping: List[str] = field(default_factory=lambda: worker_uid_maps)
    group: str = '0'
    # whether to disable procfs.
    disable_proc: bool = True
    # where to mount /tmp.
    tmpfsmount: Union[Literal[False], str] = False
    execute_fd: bool = True
    nice_level: str = '0'
    env: List[str] = field(default_factory=lambda: config.task.envp)


time_tolerance_ratio = 1.25

Profile = Literal['std', 'libc', 'valgrind', 'python']

async def run_with_limits(
    profile: Profile,
    argv: List[str],
    cwd: PosixPath,
    limits: ResourceUsage,
    *,
    infile: Union[IO[Any], int] = DEVNULL,
    outfile: Union[IO[Any], int] = DEVNULL,
    supplementary_paths: Sequence[Union[str, PosixPath]] = [],
    supplementary_paths_rw: Sequence[Union[str, PosixPath]] = [],
    network_access: bool = False,
    disable_proc: bool = True,
    tmpfsmount: bool = False,
    disable_stderr: bool = False,
    env: List[str] = [],
    setup_root_dir: Optional[Callable[[PosixPath], Coroutine[Any, Any, None]]] = None,
) -> RunResult:
    if limits.memory_bytes <= 0:
        raise ValueError('Sandbox cgroups require a positive memory limit')
    # these are nsjail args
    fsize = 'inf' if limits.file_size_bytes < 0 else \
        str(ceil(limits.file_size_bytes / 1048576 + 256))
    time_limit_scaled = limits.time_msecs * config.relative_slowness
    time_limit_nsjail = str(ceil(time_limit_scaled / 1000 * time_tolerance_ratio + 1))
    bindmount_ro = bindmount_ro_base + [str(x) for x in supplementary_paths]
    bindmount_rw = bindmount_rw_base + [str(cwd)] \
        + [str(x) for x in supplementary_paths_rw]
    if config.sandbox.pty:
        for mount in bindmount_ro + bindmount_rw:
            destination = normpath(mount.split(':', 1)[-1])
            if destination in ('/', '/dev', '/dev/ptmx', '/dev/pts') \
                    or destination.startswith(('/dev/pts/', '/dev/ptmx/')):
                raise ValueError(f'Mount would replace private PTY devices: {mount}')
    # get the absolute path for ./runner and ./du
    runner_path = str(PosixPath(__file__).with_name('runner'))
    du_path = str(PosixPath(__file__).with_name('du'))

    with TempDir() as tmp_dir, open(tmp_dir / 'stderr', 'w+b') as errfile, \
            RunCgroup(config.sandbox.cgroup_path) as cgroup:
        # make needed files and dirs
        tmp_dir.chmod(0o700)
        chroot = tmp_dir / 'root'
        chroot.mkdir(0o750)
        if setup_root_dir is not None:
            await setup_root_dir(chroot)
        result_dir = tmp_dir / 'result'
        result_dir.mkdir(0o700)
        result_file = result_dir / 'result'

        # construct nsjail args
        args = NsjailArgs(
            chroot=str(chroot),
            cwd=str(cwd),
            rlimit_fsize=fsize,
            time_limit=time_limit_nsjail,
            rlimit_cpu=str(ceil(float(time_limit_nsjail) + 1)),
            pass_fd=[str(cgroup.procs_fd)],
            bindmount_ro=bindmount_ro,
            bindmount=[str(result_dir)] + bindmount_rw,
            disable_clone_newnet=network_access,
            disable_proc=disable_proc,
            tmpfsmount='/tmp' if tmpfsmount else False,
            env=config.task.envp + env,
        )
        checker_time_limit = str(ceil(time_limit_scaled * time_tolerance_ratio + 500))
        pty_args = ['--pty'] if config.sandbox.pty else []
        run_args = [runner_path, checker_time_limit, str(result_file)] + pty_args + argv
        nsjail_argv = [profile] + pty_args + format_args(asdict(args)) + ['--'] + run_args
        argv_str = ' '.join(quote(x) for x in nsjail_argv)
        logger.debug('about to run nsjail with args %(args)s', { 'args': argv_str }, 'nsjail:run')

        # execute
        time_start = time()
        launch_args = cgroup.launcher(
            runner_path, limits.memory_bytes, config.sandbox.pids_max,
        )
        proc = Popen(
            launch_args + [nsjail_wrapper, nsjail] + nsjail_argv,
            stdin=infile, stdout=outfile,
            stderr=DEVNULL if disable_stderr else errfile,
        )
        # Leave the child unreaped until cleanup, so its PID cannot be reused.
        waiter = create_task(asyncrun(lambda: waitid(P_PID, proc.pid, WEXITED | WNOWAIT)))
        try:
            await shield(waiter)
        except BaseException:
            # Popen.kill() polls and can reap the child before our waiter.
            try:
                kill(proc.pid, SIGKILL)
            except ProcessLookupError:
                pass
            while True:
                try:
                    await shield(waiter)
                    break
                except CancelledError:
                    pass
            raise
        finally:
            _, status = waitpid(proc.pid, 0)
            code = waitstatus_to_exitcode(status)
            proc.returncode = code
        approx_time = time() - time_start
        mem = cgroup.memory_peak
        oom_killed = cgroup.oom_killed
        logger.debug('nsjail run finished with code=%(code)s approx_time=%(approx_time)s memory_peak=%(mem)s',
                     { 'code': code, 'approx_time': approx_time, 'mem': mem },
                     'nsjail:done')

        # parse result file
        try:
            if result_file.is_symlink() or not result_file.is_file():
                raise Exception('Invalid result file')
            text = result_file.read_text(errors='replace').replace('\n', '')
            # 'run' code realtime
            params = text.split(' ')
            if len(params) != 3 or params[0] != 'run':
                logger.error('invalid runner output %(output)s', { 'output': repr(text) }, 'runner:output')
                raise Exception('Invalid runner output')
            program_code, realtime = [int(x) for x in params[1:]]
            time_is_accurate = True
        except Exception:
            program_code = -1
            realtime = int(approx_time * 1000)
            time_is_accurate = False

        du_proc = await create_subprocess_exec(
            nsjail,
            *format_args(asdict(NsjailArgs('/', str(cwd), '9'))),
            '--', du_path, '-s',
            stdin=DEVNULL, stdout=PIPE, stderr=PIPE,
            limit=4096,
        )
        du_code = await wait_for(du_proc.wait(), 10.0)
        if du_code != 0:
            raise Exception(f'du exited with code {du_code}')
        assert du_proc.stdout is not None
        du_out = (await du_proc.stdout.read(4096)).decode(errors='replace') \
            .split('\n')
        file_size_bytes, file_count = [int(x) for x in du_out[:2]]
        # empty directories could still use disk storage on some FSs.
        # let's ignore them.
        if file_count == 0 and file_size_bytes < 16:
            file_size_bytes = 0
        file_size_bytes *= 1024

        usage = ResourceUsage(
            time_msecs=int(realtime / config.relative_slowness),
            memory_bytes=mem,
            file_count=file_count,
            file_size_bytes=file_size_bytes,
        )
        errfile.seek(0)
        err = '' if disable_stderr else \
            (await asyncrun(lambda: errfile.read(4096))) \
            .decode(errors='replace') \
            .replace(str(cwd), '') \
            .strip()
        errmsg = '' if err == '' else f': {err}'

        # check for errors
        if time_is_accurate and realtime > time_limit_scaled \
        or approx_time * 1000 > time_limit_scaled + 500:
            # Check needed here as some TLE'd programs end
            # up being kill -9'd by nsjail; the real time
            # won't be accurate in this case. Therefore,
            # do not move this check down after the check
            # for exit code.
            return RunResult('time_limit_exceeded', '', usage)
        if oom_killed or mem > limits.memory_bytes:
            return RunResult('memory_limit_exceeded', '', usage)
        if code != 0:
            # code is ./runner's exit code, so there must be something wrong.
            msg = f'Task runner exited with status {code}{errmsg}'
            return RunResult('system_error', msg, usage, code=code)
        if file_size_bytes > limits.file_size_bytes >= 0:
            msg = 'File size too large'
            return RunResult('disk_limit_exceeded', msg, usage)
        if file_count > limits.file_count >= 0:
            msg = 'Too many files are created'
            return RunResult('disk_limit_exceeded', msg, usage)
        if program_code != 0:
            # runner exited properly, but the program did not
            if program_code >= 512:
                # there is something wrong with the child process
                errnum = program_code - 512
                msg = f'Program did not start ({strerror(errnum)}){errmsg}'
            elif program_code >= 256:
                signal = program_code - 256
                try:
                    name = f' ({strsignal(signal)})'
                except ValueError:
                    name = ''
                msg = f'Program killed by signal {signal}{name}{errmsg}'
            elif program_code < 0 or disable_stderr:
                msg = f'Program quit abnormally{errmsg}'
            else:
                msg = f'Program exited with status {program_code}{errmsg}'
            return RunResult('runtime_error', msg, usage, code=program_code)

        # done
        return RunResult(None, err, usage)

_chown = which('chown')
assert _chown is not None
chown: str = _chown

def chown_back(path: Union[PosixPath, str]):
    logger.debug('about to chown_back %(path)s', { 'path': path }, 'tempdir:chown_back')
    cwd = PosixPath(path)
    if not cwd.is_dir():
        cwd = cwd.parent
    argv = [nsjail] + format_args({
        'cwd': str(cwd),
        'chroot': '/',
        'uid_mapping': worker_uid_maps,
        'group': '0',
        'cap': 'CAP_CHOWN',
        'really_quiet': True,
        'bindmount': str(cwd),
    }) + ['--', chown, '-R', 'root', str(path)]
    Popen(argv, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL) \
        .wait(timeout=10.0)

def chown_to_user(path: Union[PosixPath, str]):
    logger.debug('about to chown_to_user %(path)s', { 'path': path }, 'tempdir:chown_to_user')
    cwd = PosixPath(path)
    if not cwd.is_dir():
        cwd = cwd.parent
    argv = [nsjail] + format_args({
        'cwd': str(cwd),
        'chroot': '/',
        'uid_mapping': worker_uid_maps,
        'group': '0',
        'cap': 'CAP_CHOWN',
        'really_quiet': True,
        'bindmount': str(cwd),
    }) + ['--', chown, '-R', str(worker_uid_inside), str(path)]
    Popen(argv, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL) \
        .wait(timeout=10.0)
