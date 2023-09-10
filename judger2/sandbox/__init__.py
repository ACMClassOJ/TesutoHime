__all__ = 'run_with_limits', 'chown_back'

from asyncio import create_subprocess_exec, wait_for
from dataclasses import asdict, dataclass, field
from logging import getLogger
from os import WEXITSTATUS, WIFEXITED, WIFSIGNALED, WTERMSIG, getuid, wait4
from pathlib import PosixPath
from shlex import quote
from shutil import which
from signal import strsignal
from subprocess import DEVNULL, PIPE, Popen
from sys import platform
from time import time
from typing import IO, List, Union

from commons.task_typing import ResourceUsage, RunResult
from commons.util import asyncrun, Literal

from judger2.config import relative_slowness, task_envp, worker_uid
from judger2.util import TempDir, format_args

logger = getLogger(__name__)


if platform != 'linux':
    logger.critical(f'This judger runs only on Linux systems, but your system seems to be {platform}.')
    exit(2)


nsjail = PosixPath(__file__).with_name('nsjail')
if not nsjail.exists():
    raise Exception('nsjail executable not found')
nsjail = str(nsjail)

bindmount_ro_base = ['/lib', '/lib64', '/usr/lib', '/usr/lib64', '/dev/urandom']
bindmount_rw_base = ['/dev/null', '/dev/zero']
worker_uid_inside = 65534
worker_uid_maps = [
    f'0:{getuid()}:1', # map current user to 0
    f'{worker_uid_inside}:{worker_uid}:1', # map worker
]

def waitstatus_to_exitcode (status):
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
    # address space limit (mbytes) RLIMIT_AS.
    rlimit_as: str = '1536'
    # number of open file descriptors, defaults to 32 by nsjail which is too low.
    rlimit_nofile: str = '1024'

    # readonly mount points.
    bindmount_ro: Union[List[str], bool] = False
    # R/W mount points.
    bindmount: Union[List[str], bool] = False

    # maximum size in megabytes of files that the process may create.
    rlimit_fsize: str = 'inf'
    # cgroup-based memory limit: not working.
    # cgroup_mem_max: str

    # whether to enable network access in the container.
    disable_clone_newnet: bool = False

    mode: str = 'o'
    quiet: bool = True
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
    env: List[str] = field(default_factory=lambda: task_envp)


time_tolerance_ratio = 1.25

async def run_with_limits(
    argv: List[str],
    cwd: PosixPath,
    limits: ResourceUsage,
    *,
    infile: Union[IO, int] = DEVNULL,
    outfile: Union[IO, int] = DEVNULL,
    supplementary_paths: List[PosixPath] = [],
    supplementary_paths_rw: List[PosixPath] = [],
    network_access: bool = False,
    disable_proc: bool = True,
    tmpfsmount: bool = False,
    disable_stderr: bool = False,
    env: List[str] = [],
) -> RunResult:
    # these are nsjail args
    fsize = 'inf' if limits.file_size_bytes < 0 else \
        str(int(limits.file_size_bytes / 1048576 + 256))
    time_limit_scaled = limits.time_msecs * relative_slowness
    time_limit_nsjail = str(int(time_limit_scaled / 1000 * time_tolerance_ratio + 1))
    # memory_limit = str(limits.memory_bytes + 1048576)
    bindmount_ro = bindmount_ro_base + [str(x) for x in supplementary_paths]
    bindmount_rw = bindmount_rw_base + [str(cwd)] \
        + [str(x) for x in supplementary_paths_rw]
    # get the absolute path for ./runner and ./du
    runner_path = str(PosixPath(__file__).with_name('runner'))
    du_path = str(PosixPath(__file__).with_name('du'))

    with TempDir() as tmp_dir, open(tmp_dir / 'stderr', 'w+b') as errfile:
        # make needed files and dirs
        tmp_dir.chmod(0o700)
        chroot = tmp_dir / 'root'
        chroot.mkdir(0o750)
        result_dir = tmp_dir / 'result'
        result_dir.mkdir(0o700)
        result_file = result_dir / 'result'

        # construct nsjail args
        args = NsjailArgs(
            chroot=str(chroot),
            cwd=str(cwd),
            rlimit_fsize=fsize,
            time_limit=time_limit_nsjail,
            rlimit_cpu=str(int(float(time_limit_nsjail) + 1)),
            # cgroups-based memory limit is not working
            # cgroup_mem_max=memory_limit,
            bindmount_ro=bindmount_ro,
            bindmount=[str(result_dir)] + bindmount_rw,
            disable_clone_newnet=network_access,
            disable_proc=disable_proc,
            tmpfsmount='/tmp' if tmpfsmount else False,
            env=task_envp + env,
        )
        checker_time_limit = str(int(time_limit_scaled * time_tolerance_ratio + 500))
        run_args = [runner_path, checker_time_limit, str(result_file)] \
            + argv
        nsjail_argv = format_args(asdict(args)) + ['--'] + run_args
        argv_str = ' '.join(quote(x) for x in nsjail_argv)
        logger.debug(f'about to run nsjail with args {argv_str}')

        # execute
        time_start = time()
        proc = Popen(
            [nsjail] + nsjail_argv,
            stdin=infile, stdout=outfile,
            stderr=DEVNULL if disable_stderr else errfile,
        )
        _, status, rusage = await asyncrun(lambda: wait4(proc.pid, 0))
        code = waitstatus_to_exitcode(status)
        approx_time = time() - time_start
        approx_mem = rusage.ru_maxrss * 1024
        logger.debug(f'nsjail run finished')
        logger.debug(f'{code=} {approx_time=} {approx_mem=}')

        # parse result file
        try:
            text = result_file.read_text().replace('\n', '')
            # 'run' code realtime mem
            params = text.split(' ')
            if len(params) < 4 or params[0] != 'run':
                logger.error(f'invalid runner output {repr(text)}')
                raise Exception('Invalid runner output')
            program_code, realtime, mem = [int(x) for x in params[1:4]]
            usage_is_accurate = True
        except BaseException:
            program_code = -1
            realtime = int(approx_time * 1000)
            mem = int(approx_mem)
            usage_is_accurate = False

        du_proc = await create_subprocess_exec(
            nsjail,
            *format_args(asdict(NsjailArgs('/', str(cwd), '9.0'))),
            '--', du_path, '-s',
            stdin=DEVNULL, stdout=PIPE, stderr=PIPE,
            limit=4096,
        )
        du_code = await wait_for(du_proc.wait(), 10.0)
        if du_code != 0:
            raise Exception(f'du exited with code {du_code}')
        du_out = (await du_proc.stdout.read(4096)).decode(errors='replace') \
            .split('\n')
        file_size_bytes, file_count = [int(x) for x in du_out[:2]]
        # empty directories could still use disk storage on some FSs.
        # let's ignore them.
        if file_count == 0 and file_size_bytes < 16:
            file_size_bytes = 0
        file_size_bytes *= 1024

        usage = ResourceUsage(
            time_msecs=int(realtime / relative_slowness),
            memory_bytes=mem,
            file_count=file_count,
            file_size_bytes=file_size_bytes,
        )
        errfile.seek(0)
        err = '' if disable_stderr else \
            (await asyncrun(lambda: errfile.read(4096))) \
            .decode(errors='replace') \
            .replace(str(cwd), '')
        errmsg = '' if err == '' else f': {err}'

        # check for errors
        if usage_is_accurate and realtime > time_limit_scaled \
        or approx_time * 1000 > time_limit_scaled + 500:
            # Check needed here as some TLE'd programs end
            # up being kill -9'd by nsjail; the real time
            # won't be accurate in this case. Therefore,
            # do not move this check down after the check
            # for exit code.
            return RunResult('time_limit_exceeded', '', usage)
        if usage_is_accurate and mem > limits.memory_bytes:
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
            if program_code >= 256:
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


def chown_back(path: PosixPath):
    logger.debug(f'about to chown_back {path}')
    argv = [nsjail] + format_args({
        'cwd': str(path),
        'chroot': '/',
        'uid_mapping': worker_uid_maps,
        'group': '0',
        'cap': 'CAP_CHOWN',
        'quiet': True,
        'bindmount': str(path),
    }) + ['--', which('chown'), '-R', 'root', '.']
    Popen(argv, stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL) \
        .wait(timeout=10.0)
