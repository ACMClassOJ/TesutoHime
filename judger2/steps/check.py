from logging import getLogger
from math import isinf, isnan
from os import devnull
from pathlib import PosixPath
from shutil import copy2
from typing import Any, Callable, Coroutine, Dict, Optional

from commons.task_typing import (Checker, CheckInput, CheckResult,
                                 CompareChecker, DirectChecker, RunResult, SpjChecker)

from judger2.cache import ensure_cached
from judger2.config import checker_cmp_limits
from judger2.sandbox import run_with_limits
from judger2.steps.compile_ import NotCompiledException, ensure_input
from judger2.util import TempDir, copy_supplementary_files

logger = getLogger(__name__)


async def check(outfile: CheckInput, checker: Checker, run_res_path: PosixPath) -> CheckResult:
    logger.info(f'checking with {checker}')
    # get output file to check
    if not isinstance(outfile, RunResult):
        try:
            inf = None
            ouf = (await ensure_input(outfile)).path
        except NotCompiledException as e:
            return CheckResult('compile_error', str(e))
    else:
        inf = outfile.input_path
        ouf = outfile.output_path
    if ouf is None:
        return CheckResult('system_error', 'Nothing to check')

    # check
    return await checkers[checker.__class__](inf, ouf, run_res_path, checker)


cmp_errexit_code = 63

async def checker_cmp(_infile, outfile: PosixPath, run_res_path: PosixPath, checker: CompareChecker):
    cmp = PosixPath(__file__).with_name('cmp')
    ans = (await ensure_cached(checker.answer)).path
    ignore_ws_flag = 'y' if checker.ignore_whitespace else 'n'
    argv = [str(cmp), str(outfile), str(ans), ignore_ws_flag]
    logger.debug(f'about to run {argv}')
    with TempDir() as cwd:
        res = await run_with_limits(
            argv,
            cwd,
            checker_cmp_limits,
            supplementary_paths=[str(cmp), str(outfile), str(ans)],
        )
    if res.error == 'runtime_error' and res.code == cmp_errexit_code:
        return CheckResult('wrong_answer', 'Wrong answer')
    if res.error is not None:
        logger.error(f'cmp failed with {res.message}')
        return CheckResult('system_error', f'checker failed: {res.message}')
    return CheckResult('accepted', 'Accepted', 1.0)


def checker_read_float(outfile: PosixPath, message: str = ''):
    try:
        score = float(outfile.read_text())
    except ValueError:
        return CheckResult('system_error', 'Score not number')
    if isinf(score):
        return CheckResult('system_error', 'Score is infinity')
    if isnan(score):
        return CheckResult('system_error', 'Score is NaN')

    result = 'accepted' if score >= 1.0 else 'wrong_answer'
    return CheckResult(result, message, score)

async def checker_direct(_infile, outfile: PosixPath, run_res_path, _checker):
    return checker_read_float(outfile)


async def checker_spj(infile: Optional[PosixPath], outfile: PosixPath, \
    run_res_path: PosixPath, checker: SpjChecker):
    # get spj binary
    if checker.format == 'scorer':
        raise NotImplementedError()
    try:
        exe = (await ensure_input(checker.executable)).path
    except NotCompiledException as e:
        return CheckResult('system_error', f'cannot compile spj: {e}')

    # run spj
    with TempDir() as cwd:
        run_res_file = cwd / 'run_res'
        copy2(run_res_path, run_res_file)
        exec_file = cwd / 'spj'
        copy2(exe, exec_file)
        exec_file.chmod(0o550)

        await copy_supplementary_files(checker.supplementary_files, cwd)

        bindmount = ['/bin', '/usr/bin', str(outfile)]
        if infile is None:
            infile = PosixPath(devnull)
        else:
            bindmount.append(str(infile))
        if checker.answer is None:
            ans = PosixPath(devnull)
        else:
            ans = (await ensure_cached(checker.answer)).path
            bindmount.append(str(ans))
        score = cwd / 'score'
        message = cwd / 'message'
        argv = [exec_file, infile, outfile, ans, score, message, run_res_file]
        argv = [str(x) for x in argv]
        print(argv)
        logger.debug(f'about to run spj: {argv}')

        res = await run_with_limits(argv, cwd, checker.limits,
            supplementary_paths=bindmount)
        if res.error is not None:
            return CheckResult('system_error', f'checker error: {res.message}')

        msg = message.read_text() if message.exists() else ''
        return checker_read_float(score, msg)


Checker = Callable[
    [Optional[PosixPath], PosixPath, Checker],
    Coroutine[Any, Any, CheckResult],
]
checkers: Dict[Any, Checker] = {
    CompareChecker: checker_cmp,
    DirectChecker: checker_direct,
    SpjChecker: checker_spj,
}
