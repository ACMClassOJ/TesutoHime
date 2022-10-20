__all__ = ('run',)

from asyncio.subprocess import DEVNULL
from dataclasses import dataclass
from os import chmod, listdir
from pathlib import PosixPath
from shutil import copy2
from typing import Dict, List

from commons.task_typing import Input, RunArgs, RunResult
from judger2.cache import ensure_cached
from judger2.config import (java, valgrind, valgrind_args,
                            valgrind_errexit_code, verilog_interpreter)
from judger2.sandbox import run_with_limits
from judger2.steps.compile_ import NotCompiledException, ensure_input
from judger2.util import copy_supplementary_files, extract_exe_as_tar


@dataclass
class RunParams:
    argv: List[str]
    supplementary_paths: List[str]
    disable_procfs: bool = True
    tmpfsmount: bool = False

class BaseRunner:
    def prepare(self, program: PosixPath) -> RunParams:
        raise NotImplementedError()
    def interpret_result(self, result: RunResult) -> RunResult:
        return result

elf_mode = 0o550

class ElfRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        chmod(program, elf_mode)
        return RunParams([str(program)], [])

class ValgrindRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        chmod(program, elf_mode)
        argv = [valgrind] + valgrind_args + [str(program)]
        return RunParams(argv, ['/bin', '/usr/bin', '/usr/libexec'], False, True)

    def interpret_result(self, result: RunResult):
        if result.error != 'runtime_error' \
        or result.code != valgrind_errexit_code:
            return result
        res_dict = result.__dict__
        res_dict['error'] = 'memory_leak'
        res_dict['message'] = 'Memory leak'
        return RunResult(**res_dict)

class VerilogRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        argv = [verilog_interpreter, str(program)]
        return RunParams(argv, [verilog_interpreter])

class JavaRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        cwd = program.parent
        bin_path = cwd / 'bin'
        jar_name = ''
        extract_exe_as_tar(program)
        for j in listdir(cwd.as_posix()):
            if j.endswith('.jar'):
                jar_name = j
        jar_path = cwd / jar_name
        argv = [java, '-cp', f'{jar_path.as_posix()}:{bin_path.as_posix()}', 'Compiler']
        return RunParams(argv, ['/bin', '/usr/bin', '/usr/share', '/etc', bin_path, jar_path], False, True)

    def interpret_result(self, result: RunResult):
        if result.error == 'runtime_error':
            res_dict = result.__dict__
            res_dict['error'] = None
            res_dict['message'] = 'Runtime Error'
            return RunResult(**res_dict)
        return result
        

runners: Dict[str, BaseRunner] = {
    'elf': ElfRunner(),
    'valgrind': ValgrindRunner(),
    'verilog': VerilogRunner(),
    'java': JavaRunner()
}


async def run(oufdir: PosixPath, cwd: PosixPath, input: Input, args: RunArgs) \
    -> RunResult:
    # get infile
    infile = None if args.infile is None \
        else (await ensure_cached(args.infile)).path
    outfile_name = 'ouf'
    outfile = oufdir / outfile_name

    # compile if needed
    try:
        exe = await ensure_input(input)
    except NotCompiledException as e:
        return RunResult('compile_error', str(e))
    exec_file = oufdir / exe.filename
    copy2(exe.path, exec_file)
    if exe.filename == outfile_name:
        outfile = oufdir / f'{outfile_name}1'

    await copy_supplementary_files(args.supplementary_files, cwd)

    # get runner and params
    runner = runners[args.type]
    params: RunParams = runner.prepare(exec_file)

    # run
    try:
        inf = DEVNULL if infile is None else open(infile, 'r')
        with open(outfile, 'w') as ouf:
            res: RunResult = runner.interpret_result(await run_with_limits(
                params.argv,
                cwd,
                args.limits,
                supplementary_paths=[exec_file] + params.supplementary_paths,
                infile=inf,
                outfile=ouf,
                disable_stderr=True,
                disable_proc=params.disable_procfs,
                tmpfsmount=params.tmpfsmount,
            ))
    finally:
        try:
            if inf != DEVNULL and not inf.closed:
                inf.close()
        finally:
            pass

    # return result
    if res.error != None:
        return res

    return RunResult(
        error=None,
        message=res.message,
        output_path=outfile,
        resource_usage=res.resource_usage,
        input_path=infile,
    )
