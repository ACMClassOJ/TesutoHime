__all__ = 'run_with_limits', 'chown_back'

from asyncio import create_subprocess_exec, wait_for
from dataclasses import asdict, dataclass, field
from os import getuid, wait4, waitstatus_to_exitcode
from pathlib import PosixPath
from shutil import which
from subprocess import DEVNULL, Popen, PIPE
from sys import platform
from time import time
from typing import IO, Dict, Union, List

from config import relative_slowness, worker_uid, task_envp
from util import TempDir, asyncrun
from task_typing import ResourceUsage, RunResult


if platform != 'linux':
    print(f'This judger runs only on Linux systems, but your system seems to be {platform}.')
    exit(2)


def format_args (args: Dict[str, Union[bool, str, List[str]]]) -> List[str]:
    def format_arg (arg: tuple[str, Union[bool, str, List[str]]]):
        k, v = arg
        k = f'--{k}'
        if v is True:
            return [k]
        if v is False:
            return []
        if isinstance(v, list):
            return sum(map(lambda x: [k, x], v), [])
        return [k, v]
    return sum(map(format_arg, args.items()), [])


bindmount_ro_base = ['/lib', '/lib64', '/usr/lib', '/usr/lib64']
worker_uid_inside = 65534
worker_uid_maps = [
    f'0:{getuid()}:1', # map current user to 0
    f'{worker_uid_inside}:{worker_uid}:1', # map worker
]

@dataclass
class NsjailArgs:
    chroot: str
    cwd: str
    time_limit: str

    bindmount_ro: Union[List[str], bool] = False
    bindmount: Union[str, List[str], bool] = False

    rlimit_fsize: str = 'inf'
    # cgroup_mem_max: str

    disable_clone_newnet: bool = False

    mode: str = 'o'
    quiet: bool = True
    max_cpus: str = '1'
    rlimit_stack: str = 'inf'
    cap: str = 'CAP_SETUID'
    uid_mapping: List[str] = field(default_factory=lambda: worker_uid_maps)
    group: str = '0'
    disable_proc: bool = True
    execute_fd: bool = True
    nice_level: str = '0'
    env: List[str] = field(default_factory=lambda: task_envp)


async def run_with_limits (
    argv: List[str],
    cwd: PosixPath,
    limits: ResourceUsage,
    *,
    infile: IO = DEVNULL,
    outfile: IO = DEVNULL,
    supplementary_paths: List[PosixPath] = [],
    supplementary_paths_rw: List[PosixPath] = [],
    network_access: bool = False,
) -> RunResult:
    # these are nsjail args
    fsize = 'inf' if limits.file_size_bytes < 0 else \
        str(limits.file_size_bytes + 1024)
    time_limit_scaled = limits.time_msecs * relative_slowness
    time_limit = str(time_limit_scaled / 1000 + 1)
    # memory_limit = str(limits.memory_bytes + 1048576)
    bindmount_ro = bindmount_ro_base + [str(x) for x in supplementary_paths]
    bindmount_rw = [str(cwd)] + [str(x) for x in supplementary_paths_rw]
    # get the absolute path for ./runner and ./du
    runner_path = str(PosixPath(__file__).with_name('runner'))
    du_path = str(PosixPath(__file__).with_name('du'))

    with TempDir() as tmp_dir:
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
            time_limit=time_limit,
            # the memory limit does not work
            # cgroup_mem_max=memory_limit,
            bindmount_ro=bindmount_ro,
            bindmount=[str(result_dir)] + bindmount_rw,
            disable_clone_newnet=network_access,
        )
        nsjail_argv = format_args(asdict(args)) \
             + ['--', runner_path, str(result_file)] + argv
        # print(' '.join(nsjail_argv))

        # execute
        time_start = time()
        proc = Popen(
            [which('nsjail')] + nsjail_argv,
            stdin=infile, stdout=outfile, stderr=PIPE,
        )
        _, status, rusage = await asyncrun(lambda: wait4(proc.pid, 0))
        code = waitstatus_to_exitcode(status)
        approx_time = time() - time_start
        approx_mem = rusage.ru_maxrss * 1024

        # parse result file
        try:
            text = result_file.read_text().replace('\n', '')
            # 'run' code realtime mem
            params = text.split(' ')
            if len(params) < 4 or params[0] != 'run':
                raise Exception('invalid runner output')
            [program_code, realtime, mem] = [int(x) for x in params[1:4]]
            usage_is_accurate = True
        except BaseException:
            program_code = -1
            realtime = int(approx_time * 1000)
            mem = int(approx_mem)
            usage_is_accurate = False

        du_proc = await create_subprocess_exec(
            which('nsjail'),
            *format_args(asdict(NsjailArgs('/', str(cwd), '9.0'))),
            '--', du_path, '-s',
            stdin=DEVNULL, stdout=PIPE, stderr=PIPE,
            limit=4096,
        )
        du_code = await wait_for(du_proc.wait(), 10.0)
        if du_code != 0:
            raise Exception(f'du exited with code {du_code}')
        du_out = (await du_proc.stdout.read(4096)).decode().split('\n')
        [file_size_bytes, file_count] = [int(x) for x in du_out[:2]]
        file_size_bytes *= 1024

        usage = ResourceUsage(
            time_msecs=int(realtime / relative_slowness),
            memory_bytes=mem,
            file_count=file_count,
            file_size_bytes=file_size_bytes,
        )
        err = (await asyncrun(lambda: proc.stderr.read(4096))).decode()
        errmsg = '' if err == '' else f': {err}'

        # check for errors
        if usage_is_accurate and realtime > time_limit_scaled \
        or approx_time * 1000 > time_limit_scaled + 500:
            #  ^^^^^^^^^^^ Check needed here as most TLE'd
            # programs end up being kill -9'd by nsjail;
            # the real time won't be accurate in this case.
            # Therefore, do not move this check down after
            # check for exit code.
            msg = 'Time limit exceeded'
            return RunResult('time_limit_exceeded', msg, None, usage)
        if usage_is_accurate and mem > limits.memory_bytes:
            msg = 'Memory limit exceeded'
            return RunResult('memory_limit_exceeded', msg, None, usage)
        if code != 0:
            # code is ./runner's exit code, so there must be something wrong.
            msg = f'task runner exited with status {code}{errmsg}'
            return RunResult('system_error', msg, None, usage)
        if program_code != 0:
            # runner exited properly, but the program did not
            if program_code >= 256:
                msg = f'program killed by signal {program_code - 256}{errmsg}'
            elif program_code < 0:
                msg = f'program quit abnormally{errmsg}'
            else:
                msg = f'program exited with status {program_code}{errmsg}'
            return RunResult('runtime_error', msg, None, usage)
        if file_size_bytes > limits.file_size_bytes:
            msg = 'File size too large'
            return RunResult('disk_limit_exceeded', msg, None, usage)
        if file_count > limits.file_count:
            msg = 'Too many files are created'
            return RunResult('disk_limit_exceeded', msg, None, usage)

        # done
        return RunResult(None, 'OK', None, usage)


def chown_back (path: PosixPath):
    argv = [which('nsjail')] + format_args({
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