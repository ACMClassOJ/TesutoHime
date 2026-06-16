from logging import getLogger
from pathlib import PosixPath
from typing import List, Optional, Sequence
from commons.task_typing import (CompileResult, CompileTask, Input,
                                 InvalidTaskException, JudgeResult, JudgeTask, ResourceUsage,
                                 StatusUpdateProgress, Testpoint,
                                 TestpointJudgeResult)
from commons.util import format_exc
from judger2.interface import ProgressReporter
from judger2.logging_ import task_logger
from judger2.steps.compile_ import compile
from judger2.steps.run import run
from judger2.util import TempDir, copy_supplementary_files

logger = getLogger(__name__)

async def compile_task(task: CompileTask) -> CompileResult:
    try:
        return (await compile(task)).result
    except Exception as e:
        return CompileResult(result='system_error', message=format_exc(e))


def get_skip_reason(
    testpoint: Testpoint[Input],
    results: Sequence[Optional[TestpointJudgeResult]],
) -> Optional[str]:
    dep = testpoint.dependent_on
    if dep is None:
        return None

    res: List[TestpointJudgeResult] = \
        list(filter(lambda x: x is not None and x.id == dep, results))  # type: ignore
    if len(res) == 0:
        msg = f'system error: testpoint {testpoint.id} ran before dependency {dep}'
        raise InvalidTaskException(msg)
    if len(res) > 1:
        msg = f'system error: testpoint {dep} has multiple results'
        raise InvalidTaskException(msg)

    if res[0].result != 'accepted':
        return f'testpoint {dep} failed'

    return None


class Ref[T]:
    def __init__(self, value: T | None = None):
        self.value = value

async def judge_testpoint(testpoint: Testpoint[Input], result: JudgeResult, \
    cwd: PosixPath, rusage: Ref[ResourceUsage]):
    skip_reason = get_skip_reason(testpoint, result.testpoints)
    if skip_reason is not None:
        task_logger.debug('skipping testpoint %(id)s due to %(reason)s', { 'id': testpoint.id, 'reason': skip_reason }, 'testpoint:skip')
        return TestpointJudgeResult(
            id=testpoint.id,
            result='skipped',
            message=skip_reason,
        )

    with TempDir() as oufdir:
        if testpoint.run is None:
            return TestpointJudgeResult(
                id=testpoint.id,
                result='system_error',
                message='testpoint has no run step',
            )

        await copy_supplementary_files(testpoint.run.supplementary_files, cwd)
        output = await run(oufdir, cwd, testpoint.input, testpoint.run)
        logger.debug('run result: %(result)s', { 'result': output }, 'testpoint:run')
        rusage.value = output.resource_usage

        if output.error is not None:
            # include partial output even on error (e.g. timeout)
            msg = output.message or ''
            oufile = oufdir / 'ouf'
            if oufile.is_file():
                partial = oufile.read_text(errors='replace')
                if len(partial) > 4096:
                    partial = partial[:4096] + '\n...[truncated]'
                if partial.strip():
                    msg = f'{msg}\n{partial}'.strip()
            return TestpointJudgeResult(
                id=testpoint.id,
                result=output.error,
                message=msg,
                resource_usage=output.resource_usage,
            )

        # program ran successfully: accept and include output in message
        prog_output = ''
        if output.output_path is not None and output.output_path.is_file():
            prog_output = output.output_path.read_text(errors='replace')
        if len(prog_output) > 4096:
            prog_output = prog_output[:4096] + '\n...[truncated]'

        msg = output.message or ''
        if prog_output.strip():
            msg = f'{msg}\n{prog_output}'.strip()

        res = TestpointJudgeResult(
            id=testpoint.id,
            result='accepted',
            message=msg,
            score=1.0,
            resource_usage=rusage.value,
        )
        task_logger.debug('testpoint %(id)s finished with %(result)s', { 'id': testpoint.id, 'result': res }, 'testpoint:done')
        return res

async def judge_task(reporter: ProgressReporter, task: JudgeTask[Input]) -> JudgeResult:
    result = JudgeResult([None for _ in task.testpoints])
    with TempDir() as cwd:
        for i, testpoint in enumerate(task.testpoints):
            rusage = Ref[ResourceUsage](None)
            try:
                result.testpoints[i] = \
                    await judge_testpoint(testpoint, result, cwd, rusage)
            except Exception as e:
                logger.error('error judging testpoint: %(error)s', { 'error': e }, 'testpoint:error')
                result.testpoints[i] = TestpointJudgeResult(
                    id=testpoint.id,
                    result='system_error',
                    message=str(e),
                    resource_usage=rusage.value,
                )

            await reporter(StatusUpdateProgress(result))

    return result
