from pathlib import PosixPath
from shutil import copy

from cache import ensure_cached
from config import cxx, cxxflags, cxx_file_name, cxx_exec_name
from sandbox import run_with_limits
from task_typing import CompileLocalResult, CompileSourceCpp, ResourceUsage


async def compile_cpp (
    cwd: PosixPath,
    source: CompileSourceCpp,
    limits: ResourceUsage,
) -> CompileLocalResult:
    main_file = await ensure_cached(source.main)
    code_file = cwd / cxx_file_name
    exec_file = cwd / cxx_exec_name
    copy(main_file, code_file)
    res = await run_with_limits(
        [cxx] + cxxflags + [str(code_file), '-o', str(exec_file)],
        cwd, limits,
        supplementary_paths=['/bin', '/usr/bin', '/usr/include'],
    )
    if res.error != None:
        return CompileLocalResult.from_run_failure(res)
    return CompileLocalResult.from_file(exec_file)
