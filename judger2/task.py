from asyncio import CancelledError
from dataclasses import asdict
from logging import getLogger
from pathlib import PosixPath
from typing import List, Optional

from commons.task_typing import (CompileResult, CompileTask,
                                 InvalidTaskException, JudgeResult, JudgeTask,
                                 Result, Task, Testpoint, TestpointJudgeResult)

from judger2.logging_ import task_logger
from judger2.rpc import rpc
from judger2.steps.check import check
from judger2.steps.compile_ import compile
from judger2.steps.run import run
from judger2.util import TempDir, copy_supplementary_files

logger = getLogger(__name__)


async def run_task (task: Task, task_id: str) -> Result:
    type = task.type
    task_logger.info(f'received {type} task {task_id}')
    if type == 'compile':
        return await compile_task(task)
    elif type == 'judge':
        return await judge_task(task, task_id)
    else:
        raise InvalidTaskException(f'Unknown task type {type}')


async def compile_task (task: CompileTask) -> CompileResult:
    try:
        return (await compile(task)).result
    except CancelledError:
        raise
    except Exception as e:
        return CompileResult(result='system_error', message=str(e))


def get_skip_reason (
    testpoint: Testpoint,
    results: List[Optional[TestpointJudgeResult]],
) -> Optional[str]:
    dep = testpoint.dependent_on
    if dep == None:
        return None

    res = list(filter(lambda x: x != None and x.testpoint_id == dep, results))
    if len(res) == 0:
        msg = f'system error: testpoint {testpoint.id} ran before dependency {dep}'
        raise InvalidTaskException(msg)
    if len(res) > 1:
        msg = f'system error: testpoint {dep} has multiple results'
        raise InvalidTaskException(msg)

    if res[1].result != 'accepted':
        return f'testpoint {dep} failed'

    return None


class Ref:
    def __init__ (self, value):
        self.value = value

async def judge_testpoint (testpoint: Testpoint, result: JudgeResult, \
    cwd: PosixPath, rusage: Ref):
    skip_reason = get_skip_reason(testpoint, result.testpoints)
    if skip_reason != None:
        task_logger.info(f'skipping {testpoint.id} due to {skip_reason}')
        return TestpointJudgeResult(
            testpoint_id=testpoint.id,
            result='skipped',
            message=skip_reason,
        )

    with TempDir() as oufdir:
        if testpoint.run != None:
            await copy_supplementary_files(testpoint.run.supplementary_files)
            output = await run(oufdir, cwd, testpoint.input, testpoint.run)
            logger.debug(f'run result: {output}')
            rusage.value = output.resource_usage
        else:
            output = testpoint.input

        check_res = await check(output, testpoint.check)
        logger.debug(f'check result: {check_res}')
        res = TestpointJudgeResult(
            **asdict(check_res),
            testpoint_id=testpoint.id,
            resource_usage=rusage.value,
        )
        task_logger.info(f'testpoint {testpoint.id} finished with {res}')
        return res

async def judge_task (task: JudgeTask, task_id: str) -> JudgeResult:
    result = JudgeResult([None for _ in task.testpoints])
    async def report_progress ():
        await rpc('progress', {
            'id': task_id,
            'progress': asdict(result),
        })
    with TempDir() as cwd:
        for i, testpoint in enumerate(task.testpoints):
            rusage = Ref(None)
            try:
                result.testpoints[i] = \
                    judge_testpoint(testpoint, result, cwd, rusage)

            except CancelledError:
                raise
            except Exception as e:
                result.testpoints[i] = TestpointJudgeResult(
                    testpoint_id=testpoint.id,
                    result='system_error',
                    message=str(e),
                    resource_usage=rusage.value,
                )
            await report_progress()

    return result
