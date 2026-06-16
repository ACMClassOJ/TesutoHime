__all__ = 'compile', 'ensure_input'

import json
import shutil
from dataclasses import dataclass
from logging import getLogger
from os import chmod, utime
from pathlib import PosixPath
from shutil import copy2
from subprocess import DEVNULL
from tempfile import NamedTemporaryFile, mkdtemp
from time import time
from typing import Any, Callable, Coroutine, Dict, List, Type
from uuid import uuid4

from typing_extensions import TypeAlias

from commons.task_typing import (CompileLocalResult, CompileResult,
                                 CompileSource, CompileSourceCpp,
                                 CompileSourceGit, CompileSourceVerilog,
                                 CompileTask, Input, ResourceUsage)
from judger2.cache import CachedFile, ensure_cached, upload
from judger2.config import config
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
            local_path = PosixPath(config.cache_dir) / str(uuid4())
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
        return CachedFile(res.local_path, config.task.exec_file_name)
    return await ensure_cached(input.url)


async def prepare_cpp(
    cwd: PosixPath,
    source: CompileSourceCpp,
    limits: ResourceUsage,
) -> StageResult:
    main_file = (await ensure_cached(source.main)).path
    code_file = cwd / config.compiler.cxx.file_name
    copy2(main_file, code_file)
    return StageResult(True, '')

async def compile_cpp(
    cwd: PosixPath,
    source: CompileSourceCpp,
    limits: ResourceUsage,
) -> CompileLocalResult:
    code_file = cwd / config.compiler.cxx.file_name
    exec_file = cwd / config.compiler.cxx.exec_name
    res = await run_with_limits(
        'std',
        ['/bin/g++'] + config.compiler.cxx.flags + [str(code_file), '-o', str(exec_file)],
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
    logger.debug('about to compile git repo %(url)s', { 'url': source.url }, 'compile:git')

    async def run_build_step(argv: List[str], *, output = DEVNULL):
        tempfile = NamedTemporaryFile('w+')
        try:
            chmod(tempfile.name, 0o600)
            tempfile.write(config.git.ssh.private_key)
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
    git_argv = ['/bin/git', 'clone', source.url, '.'] + config.git.flags
    logger.debug('about to run %(argv)s', { 'argv': git_argv }, 'compile:git:run')
    clone_res = await run_build_step(git_argv)
    if clone_res.error is not None:
        return StageResult(False, clone_res.message)
    else:
        return StageResult(True, '')

async def _compile_chaos(
    cwd: PosixPath,
    limits: ResourceUsage,
    target_file: PosixPath,
) -> CompileLocalResult:
    """Chaos-mode compilation for git repos."""

    chaos_config = config.compiler.chaos
    assert chaos_config is not None

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
        )

    # 1. record commit hash
    with TempDir() as d, open(d / 'commit-hash', 'w+b') as ouf:
        commit_hash_argv = ['/bin/git', 'log', '-1', '--pretty=%H']
        commit_hash_res = await run_build_step(commit_hash_argv, output=ouf)
        if commit_hash_res.error is not None:
            return CompileLocalResult.from_run_failure(commit_hash_res)
        ouf.seek(0)
        commit_hash = ouf.read(128).decode().strip()
        logger.debug('git commit hash: %(commit)s', { 'commit': commit_hash }, 'compile:chaos:commit')

    # 2. overlay official chaos-tests
    chaos_tests_dest = cwd / 'chaos-tests'
    # copy to a temp location first, then rename atomically so a
    # partial copy is never left in place on failure.
    tmp_dest = PosixPath(mkdtemp(dir=str(cwd), prefix='.chaos-tests-'))
    try:
        shutil.copytree(chaos_config.tests_path, tmp_dest, symlinks=True, dirs_exist_ok=True)
        tmp_dest.chmod(0o777)
        chown_to_user(tmp_dest)
        if chaos_tests_dest.exists():
            chown_back(chaos_tests_dest)
            shutil.rmtree(chaos_tests_dest)
        tmp_dest.rename(chaos_tests_dest)
    except BaseException:
        if tmp_dest.exists():
            chown_back(tmp_dest)
            shutil.rmtree(tmp_dest)
        raise
    logger.debug('chaos-tests copied from %(src)s to %(dest)s',
                 {'src': str(chaos_config.tests_path), 'dest': str(chaos_tests_dest)},
                 'compile:chaos:copytree')

    # read test level from target file
    test_level = target_file.read_text().splitlines()[0].strip()
    if test_level not in ('basic', 'advanced', 'pressure'):
        return CompileLocalResult(
            CompileResult('compile_error',
                         f'Invalid test level "{test_level}", expected basic/advanced/pressure'),
            None,
        )
    logger.debug('chaos test level: %(level)s', {'level': test_level}, 'compile:chaos:level')

    # 3. run compile command (cargo test --no-run)
    # cwd = chaos-tests so cargo finds Cargo.toml directly.
    # Mount repo root as RW supplementary so symlinks like
    # ../../kernel/src/kernel.rs resolve.  run_with_limits will
    # deduplicate: since chaos-tests is a subpath of repo root,
    # it won't be added as a separate mount.
    cargo_home = chaos_tests_dest / '.cargo-home'
    cargo_home.mkdir(exist_ok=True)
    cargo_home.chmod(0o777)
    chown_to_user(cargo_home)
    cargo_target_dir = chaos_tests_dest / 'target'
    cargo_target_dir.mkdir(exist_ok=True)
    cargo_target_dir.chmod(0o777)
    chown_to_user(cargo_target_dir)
    message_file = cwd / 'cargo-output.json'
    with open(message_file, 'w+b') as outfile:
        cargo_argv = [
            "/bin/cargo",
            "test",
            "--no-run",
            "--message-format=json",
            f"--target-dir={chaos_tests_dest}/target",
            "--test",
            test_level,
        ]
        logger.debug('about to run %(argv)s in %(cwd)s',
                     {'argv': cargo_argv, 'cwd': str(chaos_tests_dest)}, 'compile:chaos:cargo')

        res = await run_with_limits(
            'rust-nightly', cargo_argv, chaos_tests_dest, limits,
            outfile=outfile,
            supplementary_paths_rw=[str(cwd)],
            network_access=True,
            disable_proc=False,
            env=[
                'CARGO_TERM_COLOR=never',
                f'CARGO_HOME={cargo_home}',
                f'CARGO_TARGET_DIR={chaos_tests_dest}/target',
                'RUST_BACKTRACE=1',
            ],
        )

    if res.error is not None:
        try:
            message_file.chmod(0o644)
            cargo_output = message_file.read_text(errors='replace')[:4096]
        except Exception:
            cargo_output = '(unable to read cargo output)'
        return CompileLocalResult(
            CompileResult(res.error, f'cargo test failed: {res.message}\n{cargo_output}'),
            None,
        )

    # 4. check artifact: locate the test binary from cargo JSON output
    test_binary: PosixPath | None = None
    try:
        message_file.chmod(0o644)
        for line in message_file.read_text(errors='replace').splitlines():
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get('reason') == 'compiler-artifact':
                executable = data.get('executable')
                target = data.get('target', {})
                if executable and 'test' in target.get('kind', []):
                    test_binary = PosixPath(executable)
                    if not test_binary.is_absolute():
                        test_binary = chaos_tests_dest / test_binary
                    logger.debug('found test binary: %(path)s',
                                 {'path': str(test_binary)}, 'compile:chaos:binary')
                    break
    except Exception as e:
        logger.error('error parsing cargo output: %(error)s', {'error': e}, 'compile:chaos:parse')

    if test_binary is None or not test_binary.is_file():
        return CompileLocalResult(
            CompileResult('compile_error',
                         f'Test binary not found; please ensure cargo test --no-run '
                         f'produces a test artifact'),
            None,
        )

    # 5. return result
    message = f'Using git commit {commit_hash}\nCompiled chaos test ({test_level})'
    return CompileLocalResult.from_file(test_binary, message)


async def compile_git(
    cwd: PosixPath,
    source: CompileSourceGit,
    limits: ResourceUsage,
) -> CompileLocalResult:
    # If chaos mode is configured and the target file exists in
    # supplementary files, switch to chaos compilation.
    assert config.compiler.chaos is not None
    target_file = cwd / config.compiler.chaos.target_file_name
    assert target_file.is_file()
    return await _compile_chaos(cwd, limits, target_file)


async def prepare_verilog(
    cwd: PosixPath,
    source: CompileSourceVerilog,
    limits: ResourceUsage,
) -> StageResult:
    main_file = (await ensure_cached(source.main)).path
    code_file = cwd / config.compiler.verilog.file_name
    copy2(main_file, code_file)
    return StageResult(True, '')

async def compile_verilog(
    cwd: PosixPath,
    source: CompileSourceVerilog,
    limits: ResourceUsage,
) -> CompileLocalResult:
    code_file = cwd / config.compiler.verilog.file_name
    exec_file = cwd / config.compiler.verilog.exec_name
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
