__all__ = ('run',)

from asyncio import create_task, wait
from dataclasses import dataclass
from os import chmod, close, pipe
from pathlib import PosixPath
from shutil import copy2
from subprocess import DEVNULL
from typing import IO, Dict, List, Optional, Union

from commons.task_typing import Input, RunArgs, RunResult
from commons.util import TempDir
from judger2.cache import ensure_cached, upload
from judger2.config import (python, valgrind, valgrind_args,
                            valgrind_errexit_code, verilog_interpreter)
from judger2.sandbox import run_with_limits
from judger2.steps.compile_ import NotCompiledException, ensure_input
from judger2.util import InvalidProblemException, copy_supplementary_files


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
    async def run(self, cwd: PosixPath,
                  exec_file: PosixPath, inf: Union[IO, int], ouf: Union[IO, int],
                  args: RunArgs) -> RunResult:
        params: RunParams = self.prepare(exec_file)
        return self.interpret_result(await run_with_limits(
            params.argv, cwd, args.limits,
            supplementary_paths=[exec_file] + params.supplementary_paths,  # type: ignore
            infile=inf, outfile=ouf,
            disable_stderr=True,
            disable_proc=params.disable_procfs,
            tmpfsmount=params.tmpfsmount,
        ))

elf_mode = 0o550

class ElfRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        chmod(program, elf_mode)
        return RunParams([str(program)], [])

class PythonRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        argv = [python, str(program)]
        return RunParams(argv, ['/bin', '/usr/bin', '/usr/libexec'])

class ValgrindRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        chmod(program, elf_mode)
        assert valgrind is not None
        argv = [valgrind] + valgrind_args + [str(program)]
        return RunParams(argv, ['/bin', '/usr/bin', '/usr/libexec'], False, True)

    def interpret_result(self, result: RunResult):
        if result.error != 'runtime_error' \
        or result.code != valgrind_errexit_code:
            return result
        res_dict = result.__dict__
        res_dict['error'] = 'memory_leak'
        res_dict['message'] = ''
        return RunResult(**res_dict)

class VerilogRunner(BaseRunner):
    def prepare(self, program: PosixPath):
        assert verilog_interpreter is not None
        argv = [verilog_interpreter, str(program)]
        return RunParams(argv, [verilog_interpreter])

runners: Dict[str, BaseRunner] = {
    'elf': ElfRunner(),
    'python': PythonRunner(),
    'valgrind': ValgrindRunner(),
    'verilog': VerilogRunner(),
}


async def run_interactive(cwd: PosixPath,
                          exec_file: PosixPath, infile: Optional[PosixPath], outfile: PosixPath,
                          args: RunArgs) -> RunResult:
    interactor = args.interactor
    if interactor is None:
        raise InvalidProblemException('No interactor for interactive problem')
    exe = await ensure_input(interactor.executable)
    with TempDir() as interactor_wd, TempDir() as exe_dir:
        # prepare executables
        interactor_exe = exe_dir / exe.filename
        copy2(exe.path, interactor_exe)
        chmod(interactor_exe, elf_mode)
        chmod(exec_file, elf_mode)

        # and supplementary files
        await copy_supplementary_files(interactor.supplementary_files, interactor_wd)

        # touch outfile to make bindmount work
        outfile.touch()
        outfile.chmod(0o660)

        # make pipes
        r1 = w1 = r2 = w2 = -1
        try:
            r1, w1 = pipe()
            r2, w2 = pipe()

            # run!
            runner = runners[args.type]
            task_interactor = create_task(run_with_limits(
                [str(interactor_exe), str(infile) if infile is not None else '/dev/null', str(outfile)],
                interactor_wd, interactor.limits,
                infile=r1, outfile=w2,
                supplementary_paths=['/usr', '/etc', str(interactor_exe)] + [str(infile)] if infile is not None else [],
                supplementary_paths_rw=[outfile],
            ))
            task_user = create_task(runner.run(cwd, exec_file, r2, w1, args))

            await wait([task_interactor, task_user])
            res_interactor = await task_interactor
            res_user = await task_user
        finally:
            for fd in [r1, w1, r2, w2]:
                if fd >= 0:
                    close(fd)

        # We ignore any errors on the user program, but proceed with user's resource usage
        res_interactor.resource_usage = res_user.resource_usage
        return res_interactor


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

    # run
    if args.interactor is not None:
        res = await run_interactive(cwd, exec_file, infile, outfile, args)
    else:
        runner = runners[args.type]
        try:
            inf = None if infile is None else open(infile, 'r')
            with open(outfile, 'w') as ouf:
                res = await runner.run(cwd, exec_file, DEVNULL if inf is None else inf, ouf, args)
        finally:
            try:
                if inf is not None and not inf.closed:
                    inf.close()
            finally:
                pass

    # return result
    if res.error is not None:
        return res

    # upload artifact
    if args.outfile is not None:
        await upload(outfile, args.outfile.url)

    return RunResult(
        error=None,
        message=res.message,
        output_path=outfile,
        resource_usage=res.resource_usage,
        input_path=infile,
    )
