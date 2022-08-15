from pathlib import PosixPath
from shutil import which
from typing import List

from config import git_exec_name
from sandbox import run_with_limits
from task_typing import CompileLocalResult, CompileResult, CompileSourceGit, \
                        ResourceUsage


async def compile_git (
    cwd: PosixPath,
    source: CompileSourceGit,
    limits: ResourceUsage,
) -> CompileLocalResult:
    def run_build_step (argv: List[str], network = False):
        bind = ['/bin', '/usr/bin', '/usr/include', '/usr/share/cmake']
        return run_with_limits(
            argv, cwd, limits,
            supplementary_paths=bind,
            network_access=network,
        )

    # clone
    git_argv = [which('git'), 'clone', source.url, '.', '--depth', '1']
    clone_res = await run_build_step(git_argv, True)
    if clone_res.error != None:
        return CompileLocalResult.from_run_failure(clone_res)

    # configure
    cmake_lists_path = cwd / 'CMakeLists.txt'
    if cmake_lists_path.is_file():
        res = await run_build_step([which('cmake'), '.'])
        if res.error != None:
            return CompileLocalResult.from_run_failure(res)

    # compile
    makefile_paths = [cwd / x for x in ['GNUmakefile', 'makefile', 'Makefile']]
    if any(x.is_file() for x in makefile_paths):
        res = await run_build_step([which('make')])
        if res.error != None:
            return CompileLocalResult.from_run_failure(res)

    # check
    exe = cwd / git_exec_name
    if not exe.is_file():
        msg = f'Executable \'{git_exec_name}\' not found in built files;' \
            f'please ensure your compile output is named \'{git_exec_name}\'' \
            'in the root directory of the repository.'
        return CompileLocalResult(
            CompileResult('runtime_error', msg),
            None,
        )

    # done
    return CompileLocalResult.from_file(exe)
