from asyncio import CancelledError
from dataclasses import asdict
from typing import List, Optional
from .util import TempDir

from task_typing import CompileResult, CompileTask, JudgeResult, \
                        TestpointJudgeResult, JudgeTask, Result, Task, \
                        Testpoint
from steps.compile import compile
from steps.run import run
from steps.check import check
from rpc import rpc


class InvalidTaskException (Exception): pass


async def run_task (task: Task, task_id: str) -> Result:
    type = task.type
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

async def judge_task (task: JudgeTask, task_id: str) -> JudgeResult:
    result = JudgeResult([None for _ in task.testpoints])
    for i, testpoint in enumerate(task.testpoints):
        try:
            skip_reason = get_skip_reason(testpoint, result.testpoints)
            if skip_reason != None:
                result.testpoints[i] = TestpointJudgeResult(
                    testpoint_id=testpoint.id,
                    result='skipped',
                    message=skip_reason,
                )
                continue

            with TempDir() as cwd:
                if testpoint.run != None:
                    output = await run(cwd, testpoint.input, testpoint.run)
                else:
                    output = testpoint.input

                result.testpoints[i] = await check(output, testpoint.check)
                result.testpoints[i].testpoint_id = testpoint.id

        except CancelledError:
            raise
        except Exception as e:
            result.testpoints[i] = TestpointJudgeResult(
                testpoint_id=testpoint.id,
                result='system_error',
                message=str(e),
            )

        await rpc('progress', {
            'id': task_id,
            'progress': asdict(result),
        })

    return result
