from pathlib import PosixPath
from shutil import copy

from config import verilog, verilog_file_name, verilog_exec_name
from cache import ensure_cached
from sandbox import run_with_limits
from task_typing import CompileLocalResult, CompileSourceVerilog, ResourceUsage


async def compile_verilog (
    cwd: PosixPath,
    source: CompileSourceVerilog,
    limits: ResourceUsage,
) -> CompileLocalResult:
    main_file = await ensure_cached(source.main)
    code_file = cwd / verilog_file_name
    exec_file = cwd / verilog_exec_name
    copy(main_file, code_file)
    res = await run_with_limits(
        [verilog, str(code_file), '-o', str(exec_file)],
        cwd, limits,
        supplementary_paths=['/bin', '/usr/bin'],
    )
    if res.error != None:
        return CompileLocalResult.from_run_failure(res)
    return CompileLocalResult.from_file(exec_file)
