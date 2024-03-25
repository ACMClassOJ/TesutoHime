from logging import getLogger
from math import isinf, isnan
from os import devnull
from pathlib import PosixPath
from shutil import copy2
from typing import Any, Callable, Coroutine, Dict, Literal, Optional, Type
from typing_extensions import TypeAlias

from commons.task_typing import (Checker, CheckInput, CheckResult,
                                 CompareChecker, DirectChecker, RunResult, SpjChecker)

from judger2.cache import ensure_cached
from judger2.config import checker_cmp_limits, diff
from judger2.sandbox import run_with_limits
from judger2.steps.compile_ import NotCompiledException, ensure_input
from judger2.util import TempDir, copy_supplementary_files

logger = getLogger(__name__)


async def check(outfile: CheckInput, cwd: PosixPath, checker: Checker) -> CheckResult:
    logger.debug(f'checking with {checker}')
    # get output file to check
    if not isinstance(outfile, RunResult):
        try:
            inf = None
            ouf: Optional[PosixPath] = (await ensure_input(outfile)).path
        except NotCompiledException as e:
            return CheckResult('compile_error', str(e))
    else:
        inf = outfile.input_path
        ouf = outfile.output_path
    if ouf is None:
        return CheckResult('bad_problem', 'Nothing to check')

    # check
    return await checkers[checker.__class__](inf, ouf, cwd, checker)


diff_errexit_code = 1
checker_exe = PosixPath(__file__).parent.parent / 'checker' / 'checker'
if not checker_exe.exists():
    raise Exception('checker executable not found')
checker_exe = str(checker_exe)


async def checker_cmp(_infile, outfile: PosixPath, _cwd, checker: CompareChecker):
    ans = (await ensure_cached(checker.answer)).path
    if not checker.ignore_whitespace:
        return CheckResult('system_error', 'cannot check without ignore_whitespace')
    argv = [checker_exe, '-ZB', '--', str(outfile), str(ans)] if checker.ignore_whitespace \
        else [checker_exe, '--', str(outfile), str(ans)]
    supplementary_paths = \
        ['/bin', '/usr/bin', checker_exe, str(outfile), str(ans)]
    logger.debug(f'about to run {argv}')
    with TempDir() as cwd:
        res = await run_with_limits(
            argv,
            cwd,
            checker_cmp_limits,
            supplementary_paths=supplementary_paths,
        )
    if res.error == 'runtime_error' and res.code == diff_errexit_code:
        return CheckResult('wrong_answer', '')
    if res.error is not None:
        logger.error(f'checker failed with {res.error}: {res.message}')
        return CheckResult('system_error', f'checker B failed with {res.error}: {res.message}')
    return CheckResult('accepted', '', 1.0)


def checker_read_float(outfile: PosixPath, message: str = ''):
    try:
        score = float(outfile.read_text(errors='replace'))
    except ValueError:
        return CheckResult('bad_problem', 'Invalid SPJ checker: score not number')
    if isinf(score):
        return CheckResult('bad_problem', 'Invalid SPJ checker: score is infinity')
    if isnan(score):
        return CheckResult('bad_problem', 'Invalid SPJ checker: score is NaN')

    result: Literal['accepted', 'wrong_answer'] = 'accepted' if score >= 1.0 else 'wrong_answer'
    return CheckResult(result, message, score)

async def checker_direct(_infile, outfile: PosixPath, _cwd, _checker):
    return checker_read_float(outfile)


async def checker_spj(infile: Optional[PosixPath], outfile: PosixPath, \
                      user_cwd: PosixPath, checker: SpjChecker):
    # get spj binary
    if checker.format == 'scorer':
        raise NotImplementedError()
    try:
        exe = (await ensure_input(checker.executable)).path
    except NotCompiledException as e:
        return CheckResult('bad_problem', f'cannot compile spj: {e}')

    # run spj
    with TempDir() as cwd:
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
        argv = [exec_file, infile, outfile, ans, score, message, user_cwd]
        argv = [str(x) for x in argv]
        logger.debug(f'about to run spj: {argv}')

        res = await run_with_limits(argv, cwd, checker.limits,
                                    supplementary_paths=bindmount,
                                    supplementary_paths_rw=[str(user_cwd)])
        if res.error is not None:
            return CheckResult('bad_problem', f'checker error: {res.message}')

        msg = message.read_text(errors='replace') if message.exists() else ''
        return checker_read_float(score, msg)


CheckerFunction: TypeAlias = Callable[
    [Optional[PosixPath], PosixPath, PosixPath, Checker],
    Coroutine[Any, Any, CheckResult],
]
checkers: Dict[Type[Checker], CheckerFunction] = {
    CompareChecker: checker_cmp,
    DirectChecker: checker_direct,
    SpjChecker: checker_spj,  # type: ignore
}
