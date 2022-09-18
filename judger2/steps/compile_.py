__all__ = 'compile', 'ensure_input'

from logging import getLogger
from os import utime, makedirs, walk, path, listdir
from pathlib import PosixPath
from shutil import copy2, which
from typing import Any, Callable, Coroutine, Dict, List
from uuid import uuid4

from commons.task_typing import (CompileLocalResult, CompileResult,
                                 CompileSource, CompileSourceCpp,
                                 CompileSourceGit, CompileSourceVerilog, CompileSourceGitJava,
                                 CompileTask, Input, ResourceUsage)

from judger2.cache import CachedFile, ensure_cached, upload
from judger2.config import (cache_dir, cxx, cxx_exec_name, cxx_file_name,
                            cxxflags, exec_file_name, git_exec_name, gitflags,
                            verilog, verilog_exec_name, verilog_file_name)
from judger2.sandbox import chown_back, run_with_limits
from judger2.util import TempDir, copy_supplementary_files

logger = getLogger(__name__)


async def compile(task: CompileTask) -> CompileLocalResult:
    with TempDir() as cwd:
        # copy supplementary files
        await copy_supplementary_files(task.supplementary_files, cwd)

        # compile
        type = task.source.__class__
        
        # The compiled program returned by these functions
        # reside inside cwd. As cwd is deleted once this
        # function returns, the file need to be uploaded or
        # cached for later use, and the cache location is
        # returned as a semi-persistent compile artifact
        # location.
        res = await compilers[type](cwd, task.source, task.limits)

        # check for errors
        if res.result.result != 'compiled':
            return res
        if res.local_path == None:
            return CompileLocalResult(
                result=CompileResult(
                    result='system_error',
                    message='compilation succeeded without artifact'
                ),
                local_path=None
            )
        # Chown back, or else we probably couldn't copy the
        # artifact in case the file is of mode like 0700
        # set by the compiler or by a bad mask.
        chown_back(cwd)

        # upload artifacts
        if task.artifact != None:
            local_path = (await upload(res.local_path, task.artifact.url)).path
        else:
            local_path = PosixPath(cache_dir) / str(uuid4())
            copy2(res.local_path, local_path)
            # touch the local file so the file will be eventually deleted
            utime(local_path)

        # done
        return CompileLocalResult(result=res.result, local_path=local_path)


class NotCompiledException(Exception): pass

async def ensure_input(input: Input) -> CachedFile:
    if isinstance(input, CompileTask):
        res = await compile(input)
        if res.result.result != 'compiled':
            raise NotCompiledException(res.result.message)
        return CachedFile(res.local_path, exec_file_name)
    return await ensure_cached(input.url)


async def compile_cpp(
    cwd: PosixPath,
    source: CompileSourceCpp,
    limits: ResourceUsage,
) -> CompileLocalResult:
    main_file = (await ensure_cached(source.main)).path
    code_file = cwd / cxx_file_name
    exec_file = cwd / cxx_exec_name
    copy2(main_file, code_file)
    res = await run_with_limits(
        [cxx] + cxxflags + [str(code_file), '-o', str(exec_file)],
        cwd, limits,
        supplementary_paths=['/bin', '/usr/bin', '/usr/include'],
    )
    if res.error != None:
        return CompileLocalResult.from_run_failure(res)
    return CompileLocalResult.from_file(exec_file)


def get_resolv_conf_path():
    resolv_conf = PosixPath('/etc/resolv.conf')
    if not resolv_conf.exists():
        return None
    if not resolv_conf.is_symlink():
        return None
    return str(resolv_conf.resolve())

resolv_conf_path = get_resolv_conf_path()

async def compile_git(
    cwd: PosixPath,
    source: CompileSourceGit,
    limits: ResourceUsage,
) -> CompileLocalResult:
    logger.debug(f'about to compile git repo {repr(source.url)}')

    def run_build_step(argv: List[str], network = False):
        bind = ['/bin', '/usr/bin', '/usr/include', '/usr/share', '/etc']
        if resolv_conf_path is not None:
            bind.append(resolv_conf_path)
        return run_with_limits(
            argv, cwd, limits,
            supplementary_paths=bind,
            network_access=network,
        )

    # clone
    git_argv = [which('git'), 'clone', source.url, '.'] + gitflags
    logger.debug(f'about to run {git_argv}')
    clone_res = await run_build_step(git_argv, True)
    if clone_res.error != None:
        return CompileLocalResult.from_run_failure(clone_res)

    # configure
    cmake_lists_path = cwd / 'CMakeLists.txt'
    if cmake_lists_path.is_file():
        logger.debug('CMake config found, invoking cmake')
        res = await run_build_step([which('cmake'), '.'])
        if res.error != None:
            return CompileLocalResult.from_run_failure(res)

    # compile
    makefile_paths = [cwd / x for x in ['GNUmakefile', 'makefile', 'Makefile']]
    if any(x.is_file() for x in makefile_paths):
        logger.debug('makefile found, invoking make')
        res = await run_build_step([which('make')])
        if res.error != None:
            return CompileLocalResult.from_run_failure(res)

    # check
    exe = cwd / git_exec_name
    if not exe.is_file():
        msg = f'Executable \'{git_exec_name}\' not found in built files; ' \
            f'please ensure your compile output is named \'{git_exec_name}\' ' \
            'in the root directory of the repository.'
        return CompileLocalResult(
            CompileResult('runtime_error', msg),
            None,
        )

    # done
    return CompileLocalResult.from_file(exe)


async def compile_verilog(
    cwd: PosixPath,
    source: CompileSourceVerilog,
    limits: ResourceUsage,
) -> CompileLocalResult:
    main_file = (await ensure_cached(source.main)).path
    code_file = cwd / verilog_file_name
    exec_file = cwd / verilog_exec_name
    copy2(main_file, code_file)
    res = await run_with_limits(
        [verilog, str(code_file), '-o', str(exec_file)],
        cwd, limits,
        supplementary_paths=['/bin', '/usr/bin'],
        tmpfsmount=True,
    )
    if res.error != None:
        return CompileLocalResult.from_run_failure(res)
    return CompileLocalResult.from_file(exec_file)


async def compile_git_java(
    cwd: PosixPath,
    source: CompileSourceGitJava,
    limits: ResourceUsage,
) -> CompileLocalResult:
    logger.debug(f'about to compile git repo {repr(source.url)}')

    def run_build_step(argv: List[str], network = False):
        bind = ['/bin', '/usr/bin', '/usr/include', '/usr/share', '/etc']
        if resolv_conf_path is not None:
            bind.append(resolv_conf_path)
        return run_with_limits(
            argv, cwd, limits,
            supplementary_paths=bind,
            network_access=network,
            disable_proc=False
        )

    # clone
    git_argv = [which('git'), 'clone', source.url, '.'] + gitflags
    logger.debug(f'about to run {git_argv}')
    clone_res = await run_build_step(git_argv, True)
    if clone_res.error != None:
        return CompileLocalResult.from_run_failure(clone_res)

    # compile
    src_path = cwd / 'src'
    src_txt = cwd / 'src.txt'
    bin_path = cwd / 'bin'
    bin_tar = cwd / 'code.tar.gz'
    jar_name = ''
    for j in listdir(cwd.as_posix()):
        if j.endswith('.jar'):
            jar_name = j
    jar_path = cwd / jar_name
    makedirs(bin_path.as_posix())
    with open(src_txt.as_posix(), 'w') as src:
        for root, dirs, files in walk(src_path.as_posix()):
            for name in files:
                if name.endswith('.java'):
                    src.write(path.join(root, name) + '\n')
    res = await run_build_step([which('javac'), '@' + src_txt.as_posix(),'-encoding', 'UTF8', 
          '-d', bin_path.as_posix(), '-cp', jar_path.as_posix()])
    if res.error != None:
        return CompileLocalResult.from_run_failure(res)
    res = await run_build_step([which('tar'), '-czvf', bin_tar.as_posix(), './bin', jar_name])
    if res.error != None:
        return CompileLocalResult.from_run_failure(res)

    # check
    if not bin_tar.is_file():
        msg = f'Java class tarball not found.'
        return CompileLocalResult(
            CompileResult('runtime_error', msg),
            None,
        )

    # done
    return CompileLocalResult.from_file(bin_tar)


Compiler = Callable[
    [PosixPath, CompileSource, ResourceUsage],
    Coroutine[Any, Any, CompileLocalResult],
]
compilers: Dict[Any, Compiler] = {
    CompileSourceCpp: compile_cpp,
    CompileSourceGit: compile_git,
    CompileSourceVerilog: compile_verilog,
    CompileSourceGitJava: compile_git_java,
}
