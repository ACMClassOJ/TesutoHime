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
from judger2.config import checker_cmp_limits
from judger2.sandbox import run_with_limits
from judger2.steps.compile_ import NotCompiledException, ensure_input
from judger2.util import TempDir, copy_supplementary_files

logger = getLogger(__name__)


async def check(outfile: CheckInput, cwd: PosixPath, checker: Checker) -> CheckResult:
    logger.debug('checking with %(checker)s', { 'checker': checker }, 'check:start')
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


checker_errexit_code = 1
checker_exe = '/bin/acmoj-checker'


async def checker_cmp(_infile, outfile: PosixPath, _cwd, checker: CompareChecker):
    ans = (await ensure_cached(checker.answer)).path
    argv = [checker_exe, '-ZB', '--', str(outfile), str(ans)] if checker.ignore_whitespace \
        else [checker_exe, '--', str(outfile), str(ans)]
    logger.debug('about to run %(argv)s', { 'argv': argv }, 'checker:cmp')
    with TempDir() as cwd:
        res = await run_with_limits(
            'std', argv, cwd,
            checker_cmp_limits,
            supplementary_paths=[outfile, ans],
        )
    if res.error == 'runtime_error' and res.code == checker_errexit_code:
        return CheckResult('wrong_answer', '')
    if res.error is not None:
        logger.error('checker failed with %(error)s: %(message)s', { 'error': res.error, 'message': res.message }, 'checker:cmp')
        return CheckResult('system_error', f'checker failed with {res.error}: {res.message}')
    return CheckResult('accepted', '', 1.0)


def checker_read_float(outfile: PosixPath, message: str = ''):
    try:
        if outfile.is_symlink():
            return CheckResult('bad_problem', 'Invalid score: score cannot be a symlink')
        if not outfile.is_file():
            return CheckResult('bad_problem', 'Invalid score: score is not regular file')
        text = outfile.read_text(errors='replace').splitlines(keepends=True)
        score = float(text[0])
        message += ''.join(text[1:])
    except IndexError:
        return CheckResult('bad_problem', 'Invalid score: score is empty')
    except ValueError:
        return CheckResult('bad_problem', 'Invalid score: score not number')
    except PermissionError:
        return CheckResult('bad_problem', 'Invalid score: cannot read score file')
    if isinf(score):
        return CheckResult('bad_problem', 'Invalid score: score is infinity')
    if isnan(score):
        return CheckResult('bad_problem', 'Invalid score: score is NaN')

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

        bindmount = [str(outfile)]
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
        logger.debug('about to run spj: %(argv)s', { 'argv': argv }, 'checker:spj')

        res = await run_with_limits('std', argv, cwd, checker.limits,
                                    supplementary_paths=bindmount,
                                    supplementary_paths_rw=[user_cwd])
        if res.error is not None:
            return CheckResult('bad_problem', f'checker error: {res.message}')

        try:
            msg = ''
            if message.exists():
                if message.is_symlink():
                    return CheckResult('bad_problem', 'Message file cannot be a symlink')
                if not message.is_file():
                    return CheckResult('bad_problem', 'Message file is not a regular file')
                msg = message.read_text(errors='replace')
        except PermissionError:
            return CheckResult('bad_problem', 'Unable to read message file')
        return checker_read_float(score, msg)


CheckerFunction: TypeAlias = Callable[
    [Optional[PosixPath], PosixPath, PosixPath, Checker],
    Coroutine[Any, Any, CheckResult],
]
checkers: Dict[Type[Checker], CheckerFunction] = {
    CompareChecker: checker_cmp,  # type: ignore
    DirectChecker: checker_direct,
    SpjChecker: checker_spj,  # type: ignore
}
