__all__ = ('run',)

from asyncio.subprocess import DEVNULL
from dataclasses import dataclass
from os import chmod
from pathlib import PosixPath
from shutil import copy2, which
from typing import Dict, List

from commons.task_typing import Input, ResourceUsage, RunArgs, RunResult
from judger2.cache import ensure_cached, upload
from judger2.config import (resolv_conf_path, valgrind, valgrind_args,
                            valgrind_errexit_code, verilog_interpreter)
from judger2.logging_ import getLogger
from judger2.sandbox import run_with_limits
from judger2.steps.compile_ import NotCompiledException, ensure_input
from judger2.util import copy_supplementary_files

logger = getLogger(__name__)

@dataclass
class RunParams:
    argv: List[str]
    supplementary_paths: List[str]
    disable_procfs: bool = True
    tmpfsmount: bool = False

class BaseRunner:
    async def prepare(self, program: PosixPath, args: RunArgs) -> RunParams:
        raise NotImplementedError()
    def interpret_result(self, result: RunResult, outfile) -> RunResult:
        return result

elf_mode = 0o550

class ElfRunner(BaseRunner):
    async def prepare(self, program: PosixPath, args: RunArgs):
        chmod(program, elf_mode)
        return RunParams([str(program)], [])

class ValgrindRunner(BaseRunner):
    async def prepare(self, program: PosixPath, args: RunArgs):
        chmod(program, elf_mode)
        argv = [valgrind] + valgrind_args + [str(program)]
        return RunParams(argv, ['/bin', '/usr/bin', '/usr/libexec'], False, True)

    def interpret_result(self, result: RunResult, ouf):
        if result.error != 'runtime_error' \
        or result.code != valgrind_errexit_code:
            return result
        res_dict = result.__dict__
        res_dict['error'] = 'memory_leak'
        res_dict['message'] = ''
        return RunResult(**res_dict)

class VerilogRunner(BaseRunner):
    async def prepare(self, program: PosixPath, args: RunArgs):
        argv = [verilog_interpreter, str(program)]
        return RunParams(argv, [verilog_interpreter])

class CompilerRunner(BaseRunner):
    async def prepare(self, program: PosixPath, args: RunArgs):
        bind = ['/bin', '/usr/bin', '/usr/include', '/usr/share', '/etc']
        if resolv_conf_path is not None:
            bind.append(resolv_conf_path)
        bin_dir = program.parent / 'bin'
        tar_argv = [which('tar'), '--zstd', '-xf', str(program)]
        limits = ResourceUsage(
            time_msecs=10 * 1000,
            memory_bytes=1 * 1024 ** 3,
            file_count=-1,
            file_size_bytes=-1,
        )
        mkdir_res = await run_with_limits(
            [which('mkdir'), 'bin'], program.parent, limits,
            supplementary_paths=bind,
        )
        if mkdir_res.error != None:
            logger.error(f'Unable to decompress build artifact: {mkdir_res.message}')
            raise RuntimeError(mkdir_res.message)
        tar_res = await run_with_limits(
            tar_argv, bin_dir, limits,
            supplementary_paths=bind,
            supplementary_paths_rw=[program.parent],
            bindmount_cwd=False,
            network_access=True,
            disable_proc=False,
            tmpfsmount=True,
        )
        if tar_res.error != None:
            logger.error(f'Unable to decompress build artifact: {tar_res.message}')
            raise RuntimeError(tar_res.message)
        bind.append(bin_dir)
        return RunParams([str(bin_dir / 'mxc'), args.compiler_stage], bind, False, True)

    def interpret_result(self, result: RunResult, outfile):
        if result.error != 'runtime_error':
            return result
        res_dict = result.__dict__
        res_dict['error'] = None
        res_dict['message'] = ''
        with open(outfile, 'w') as ouf:
            ouf.write('runtime_error')
        return RunResult(**res_dict)

runners: Dict[str, BaseRunner] = {
    'elf': ElfRunner(),
    'valgrind': ValgrindRunner(),
    'verilog': VerilogRunner(),
    'compiler': CompilerRunner(),
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
    params: RunParams = await runner.prepare(exec_file, args)

    # run
    try:
        inf = DEVNULL if infile is None else open(infile, 'r')
        with open(outfile, 'w') as ouf:
            res: RunResult = await run_with_limits(
                params.argv,
                cwd,
                args.limits,
                supplementary_paths=[exec_file] + params.supplementary_paths,
                infile=inf,
                outfile=ouf,
                disable_stderr=True,
                disable_proc=params.disable_procfs,
                tmpfsmount=params.tmpfsmount,
            )
        res = runner.interpret_result(res, outfile)
    finally:
        try:
            if inf != DEVNULL and not inf.closed:
                inf.close()
        finally:
            pass

    # return result
    if res.error != None:
        return res

    # upload artifact
    if args.outfile != None:
        await upload(outfile, args.outfile.url)

    return RunResult(
        error=None,
        message=res.message,
        output_path=outfile,
        resource_usage=res.resource_usage,
        input_path=infile,
    )
