from asyncio import CancelledError
from logging import getLogger
from pathlib import PosixPath
from typing import List, Optional, Sequence, Union

from typing_extensions import overload

from commons.task_typing import (Artifact, CompileResult, CompileTask, Input,
                                 InvalidTaskException, JudgeResult, JudgeTask,
                                 RunResult, StatusUpdateProgress, Testpoint,
                                 TestpointJudgeResult)
from commons.util import format_exc, serialize
from judger2.config import queues, redis, task_timeout_secs
from judger2.logging_ import task_logger
from judger2.steps.check import check
from judger2.steps.compile_ import compile
from judger2.steps.run import run
from judger2.util import TempDir, copy_supplementary_files

logger = getLogger(__name__)


@overload
async def run_task(task: CompileTask, task_id: str) -> CompileResult: pass
@overload
async def run_task(task: JudgeTask[Input], task_id: str) -> JudgeResult: pass
async def run_task(task, task_id):
    task_logger.info(f'received task {task_id}')
    task_logger.debug(f'received task {task_id}: {task}')
    if isinstance(task, CompileTask):
        return await compile_task(task)
    elif isinstance(task, JudgeTask):
        return await judge_task(task, task_id)
    else:
        raise InvalidTaskException(f'Unknown task type')


async def compile_task(task: CompileTask) -> CompileResult:
    try:
        return (await compile(task)).result
    except CancelledError:
        return CompileResult(result='aborted', message='')
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


class Ref:
    def __init__(self, value):
        self.value = value

async def judge_testpoint(testpoint: Testpoint[Input], result: JudgeResult, \
    cwd: PosixPath, rusage: Ref):
    skip_reason = get_skip_reason(testpoint, result.testpoints)
    if skip_reason is not None:
        task_logger.debug(f'skipping {testpoint.id} due to {skip_reason}')
        return TestpointJudgeResult(
            id=testpoint.id,
            result='skipped',
            message=skip_reason,
        )

    with TempDir() as oufdir:
        output: Union[CompileTask, Artifact, RunResult]
        if testpoint.run is not None:
            await copy_supplementary_files(testpoint.run.supplementary_files,
                cwd)
            output = await run(oufdir, cwd, testpoint.input, testpoint.run)
            logger.debug(f'run result: {output}')
            rusage.value = output.resource_usage
            if output.error is not None:
                return TestpointJudgeResult(
                    id=testpoint.id,
                    result=output.error,
                    message=output.message,
                    resource_usage=output.resource_usage,
                )
        else:
            output = testpoint.input

        check_res = await check(output, cwd, testpoint.check)
        logger.debug(f'check result: {check_res}')
        res = TestpointJudgeResult(
            **check_res.__dict__,
            id=testpoint.id,
            resource_usage=rusage.value,
        )
        task_logger.debug(f'testpoint {testpoint.id} finished with {res}')
        return res

async def judge_task(task: JudgeTask[Input], task_id: str) -> JudgeResult:
    result = JudgeResult([None for _ in task.testpoints])  # type: ignore
    with TempDir() as cwd:
        for i, testpoint in enumerate(task.testpoints):
            rusage = Ref(None)
            try:
                result.testpoints[i] = \
                    await judge_testpoint(testpoint, result, cwd, rusage)

            except CancelledError:
                return result
            except Exception as e:
                logger.error(f'Error judging testpoint: {format_exc(e)}')
                result.testpoints[i] = TestpointJudgeResult(
                    id=testpoint.id,
                    result='system_error',
                    message=str(e),
                    resource_usage=rusage.value,
                )

            queue = queues.task(task_id).progress
            await redis.lpush(queue, serialize(StatusUpdateProgress(result)))
            await redis.expire(queue, task_timeout_secs)

    return result
