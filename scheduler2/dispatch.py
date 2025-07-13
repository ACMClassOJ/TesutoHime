from asyncio import FIRST_COMPLETED, CancelledError, create_task, sleep, wait
from logging import getLogger
from time import time
from typing import Awaitable, Callable, Optional
from uuid import uuid4

from typing_extensions import overload

from commons.task_typing import (CompileResult, CompileTask, Input,
                                 JudgeResult, JudgeTask, StatusUpdate,
                                 StatusUpdateDone, StatusUpdateError,
                                 StatusUpdateProgress, StatusUpdateStarted)
from scheduler2.config import (task_retries, task_retry_interval_secs,
                               task_timeout_secs)
from scheduler2.rpc.runner.client import RunnerOfflineException, task_abort, task_enqueue, task_progress_wait, wait_until_offline
from scheduler2.state.rate_limit import rate_limiter
from scheduler2.state.runner_tasks import RunnerTaskInfo, deregister_runner_task, register_runner_task

logger = getLogger(__name__)


@overload
async def run_task(
    taskinfo: RunnerTaskInfo[CompileTask],
    onprogress: Optional[Callable[[StatusUpdate], Awaitable]] = None,
    rate_limit_group: Optional[str] = None,
    retries_left: int = task_retries,
) -> CompileResult: pass
@overload
async def run_task(
    taskinfo: RunnerTaskInfo[JudgeTask[Input]],
    onprogress: Optional[Callable[[StatusUpdate], Awaitable]] = None,
    rate_limit_group: Optional[str] = None,
    retries_left: int = task_retries,
) -> JudgeResult: pass
async def run_task(taskinfo, onprogress = None, rate_limit_group = None,
                   retries_left = task_retries):
    task_id = str(uuid4())
    taskinfo.id = task_id
    task = taskinfo.task
    register_runner_task(taskinfo)

    async def retry(msg):
        if retries_left <= 0:
            logger.warning('task %(id)s failed: %(message)s', { 'id': task_id, 'message': msg }, 'task:fail')
            raise Exception(msg)
        logger.info('task %(id)s failed: %(message)s, retrying', { 'id': task_id, 'message': msg }, 'task:retry')
        await sleep(task_retry_interval_secs)
        return await run_task(taskinfo, onprogress, rate_limit_group,
            retries_left - 1)

    try:
        async with rate_limiter.limit(rate_limit_group):
            logger.debug('running task %(id)s: %(task)s', { 'id': task_id, 'task': task }, 'task:start')

            await task_enqueue(taskinfo)
            task_timeout = time() + task_timeout_secs

            offline_task = None
            try:
                while True:
                    progress_task = create_task(task_progress_wait(task_id, task_timeout - time()))
                    tasks = (progress_task,)
                    if offline_task is not None:
                        tasks = (progress_task, offline_task)
                    done, _ = await wait(tasks, return_when=FIRST_COMPLETED)
                    status = None
                    for done_task in done:
                        try:
                            status = await done_task
                        except RunnerOfflineException:
                            return await retry('Runner offline')
                    if status is None:
                        return await retry('Task timed out')
                    logger.debug('received status update from task %(id)s: %(status)s', { 'id': task_id, 'status': status }, 'task:update')

                    if isinstance(status, StatusUpdateStarted):
                        offline_task = wait_until_offline(status.id)
                        if onprogress is not None:
                            await onprogress(status)
                    elif isinstance(status, StatusUpdateProgress):
                        if onprogress is not None:
                            await onprogress(status)
                    elif isinstance(status, StatusUpdateDone):
                        return status.result
                    elif isinstance(status, StatusUpdateError):
                        message = status.message
                        msg = f'Runner error: {message}'
                        logger.error(msg)
                        return await retry(msg)
                    else:
                        raise Exception(f'Unknown message from runner: {status}')
            except CancelledError:
                logger.info('aborting task %(id)s', { 'id': task_id }, 'task:abort')
                await task_abort(task_id)
                raise
    finally:
        deregister_runner_task(taskinfo)
