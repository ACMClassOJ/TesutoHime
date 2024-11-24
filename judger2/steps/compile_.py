__all__ = 'compile', 'ensure_input'

from dataclasses import dataclass
from logging import getLogger
from os import chmod, utime
from pathlib import PosixPath
from shutil import copy2
from subprocess import DEVNULL
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Coroutine, Dict, List, Type
from uuid import uuid4

from typing_extensions import TypeAlias

from commons.task_typing import (CompileLocalResult, CompileResult,
                                 CompileSource, CompileSourceCpp,
                                 CompileSourceGit, CompileSourceVerilog,
                                 CompileTask, Input, ResourceUsage)
from judger2.cache import CachedFile, ensure_cached, upload
from judger2.config import (cache_dir, cxx_exec_name, cxx_file_name, cxxflags,
                            exec_file_name, git_exec_name, git_ssh_private_key,
                            gitflags, verilog_exec_name, verilog_file_name)
from judger2.sandbox import chown_back, chown_to_user, run_with_limits
from judger2.util import (FileConflictException, TempDir,
                          copy_supplementary_files)

logger = getLogger(__name__)

@dataclass
class StageResult:
    success: bool
    message: str

async def compile(task: CompileTask) -> CompileLocalResult:
    with TempDir() as cwd:
        type = task.source.__class__
        # prepare
        result = await prepareStages[type](cwd, task.source, task.limits)
        if result.success is False:
            return CompileLocalResult(
                CompileResult(result='compile_error', message=result.message),
                local_path=None,
            )

        # copy supplementary files
        # This part should be done after the prepare stage in order to copy
        # the supplementary files to the correct directory (e.g, git repo).
        try:
            await copy_supplementary_files(task.supplementary_files, cwd)
        except FileConflictException as e:
            return CompileLocalResult(
                CompileResult(result='compile_error', message=str(e)),
                local_path=None,
            )

        # compile
        # The compiled program returned by these functions
        # reside inside cwd. As cwd is deleted once this
        # function returns, the file need to be uploaded or
        # cached for later use, and the cache location is
        # returned as a semi-persistent compile artifact
        # location.
        res = await compileStages[type](cwd, task.source, task.limits)

        # check for errors
        if res.result.result != 'compiled':
            return res
        if res.local_path is None:
            return CompileLocalResult(
                result=CompileResult(
                    result='system_error',
                    message='compilation succeeded without artifact',
                ),
                local_path=None,
            )
        if res.local_path.is_symlink():
            return CompileLocalResult(
                result=CompileResult(
                    result='runtime_error',
                    message='compile artifact cannot be a symlink',
                ),
                local_path=None,
            )
        # Chown back, or else we probably couldn't copy the
        # artifact in case the file is of mode like 0700
        # set by the compiler or by a bad mask.
        chown_back(cwd)

        # upload artifacts
        if task.artifact is not None:
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
        assert res.local_path is not None
        return CachedFile(res.local_path, exec_file_name)
    return await ensure_cached(input.url)



async def prepare_cpp(
    cwd: PosixPath,
    source: CompileSourceCpp,
    limits: ResourceUsage,
) -> StageResult:
    main_file = (await ensure_cached(source.main)).path
    code_file = cwd / cxx_file_name
    copy2(main_file, code_file)
    return StageResult(True, '')

async def compile_cpp(
    cwd: PosixPath,
    source: CompileSourceCpp,
    limits: ResourceUsage,
) -> CompileLocalResult:
    code_file = cwd / cxx_file_name
    exec_file = cwd / cxx_exec_name
    res = await run_with_limits(
        'std',
        ['/bin/g++'] + cxxflags + [str(code_file), '-o', str(exec_file)],
        cwd, limits,
    )
    if res.error is not None:
        return CompileLocalResult.from_run_failure(res)
    return CompileLocalResult.from_file(exec_file, res.message)


async def prepare_git(
    cwd: PosixPath,
    source: CompileSourceGit,
    limits: ResourceUsage,
) -> StageResult:
    logger.debug(f'about to compile git repo {repr(source.url)}')

    async def run_build_step(argv: List[str], *, output = DEVNULL):
        tempfile = NamedTemporaryFile('w+')
        try:
            chmod(tempfile.name, 0o600)
            tempfile.write(git_ssh_private_key)
            tempfile.flush()
            chown_to_user(tempfile.name)
            bind = [
                f'{tempfile.name}:/id_acmoj',
            ]
            return await run_with_limits(
                'std', argv, cwd, limits,
                outfile=output,
                supplementary_paths=bind,
                network_access=True,
                env=[
                    'GIT_CONFIG_COUNT=2',
                    'GIT_CONFIG_KEY_0=safe.directory',
                    'GIT_CONFIG_VALUE_0=*',
                    'GIT_CONFIG_KEY_1=url.git@github.com:.insteadOf',
                    'GIT_CONFIG_VALUE_1=https://github.com/'
                ],
            )
        finally:
            chown_back(tempfile.name)
            tempfile.close()
    
    # clone
    git_argv = ['/bin/git', 'clone', source.url, '.'] + gitflags
    logger.debug(f'about to run {git_argv}')
    clone_res = await run_build_step(git_argv)
    if clone_res.error is not None:
        return StageResult(False, clone_res.message)
    else:
        return StageResult(True, '')

async def compile_git(
    cwd: PosixPath,
    source: CompileSourceGit,
    limits: ResourceUsage,
) -> CompileLocalResult:
    async def run_build_step(argv: List[str], *, output = DEVNULL):
        return await run_with_limits(
            'std', argv, cwd, limits,
            outfile=output,
            network_access=False,
            env=[
                'GIT_CONFIG_COUNT=2',
                'GIT_CONFIG_KEY_0=safe.directory',
                'GIT_CONFIG_VALUE_0=*',
                'GIT_CONFIG_KEY_1=url.git@github.com:.insteadOf',
                'GIT_CONFIG_VALUE_1=https://github.com/'
            ],
            tmpfsmount=True,
        )

    # get commit hash
    with TempDir() as d, open(d / 'commit-hash', 'w+b') as ouf:
        commit_hash_argv = ['/bin/git', 'log', '-1', '--pretty=%H']
        commit_hash_res = await run_build_step(commit_hash_argv, output=ouf)
        if commit_hash_res.error is not None:
            return CompileLocalResult.from_run_failure(commit_hash_res)
        ouf.seek(0)
        commit_hash = ouf.read(128).decode().strip()
        logger.debug(f'git commit hash: {commit_hash}')
        message = f'Using git commit {commit_hash}'

    # configure
    cmake_lists_path = cwd / 'CMakeLists.txt'
    if cmake_lists_path.is_file():
        logger.debug('CMake config found, invoking cmake')
        res = await run_build_step(['/bin/cmake', '.'])
        if res.error is not None:
            return CompileLocalResult.from_run_failure(res)
    else:
        message += '\nWarning: CMakeLists.txt not found, skipping cmake invocation'

    # compile
    makefile_paths = [cwd / x for x in ['GNUmakefile', 'makefile', 'Makefile']]
    if any(x.is_file() for x in makefile_paths):
        logger.debug('makefile found, invoking make')
        res = await run_build_step(['/bin/make'])
        if res.error is not None:
            return CompileLocalResult.from_run_failure(res)
    else:
        message += '\nWarning: Makefile not found, skipping make invocation'

    # check
    exe = cwd / git_exec_name
    if not exe.is_file():
        msg = message + '\n' + \
            f'Executable \'{git_exec_name}\' not found in built files; ' \
            f'please ensure your compile output is named \'{git_exec_name}\' ' \
            'in the root directory of the repository.'
        return CompileLocalResult(
            CompileResult('runtime_error', msg),
            None,
        )

    # done
    return CompileLocalResult.from_file(exe, message)


async def prepare_verilog(
    cwd: PosixPath,
    source: CompileSourceVerilog,
    limits: ResourceUsage,
) -> StageResult:
    main_file = (await ensure_cached(source.main)).path
    code_file = cwd / verilog_file_name
    copy2(main_file, code_file)
    return StageResult(True, '')

async def compile_verilog(
    cwd: PosixPath,
    source: CompileSourceVerilog,
    limits: ResourceUsage,
) -> CompileLocalResult:
    code_file = cwd / verilog_file_name
    exec_file = cwd / verilog_exec_name
    res = await run_with_limits(
        'std',
        ['/bin/iverilog', str(code_file), '-o', str(exec_file)],
        cwd, limits,
        tmpfsmount=True,
    )
    if res.error is not None:
        return CompileLocalResult.from_run_failure(res)
    return CompileLocalResult.from_file(exec_file)

PrepareStage: TypeAlias = Callable[
    [PosixPath, CompileSource, ResourceUsage],
    Coroutine[Any, Any, StageResult],
]
prepareStages: Dict[Type[CompileSource], PrepareStage] = {
    CompileSourceCpp: prepare_cpp,  # type: ignore
    CompileSourceGit: prepare_git,  # type: ignore
    CompileSourceVerilog: prepare_verilog,  # type: ignore
}

CompileStage: TypeAlias = Callable[
    [PosixPath, CompileSource, ResourceUsage],
    Coroutine[Any, Any, CompileLocalResult],
]
compileStages: Dict[Type[CompileSource], CompileStage] = {
    CompileSourceCpp: compile_cpp,  # type: ignore
    CompileSourceGit: compile_git,  # type: ignore
    CompileSourceVerilog: compile_verilog,  # type: ignore
}
