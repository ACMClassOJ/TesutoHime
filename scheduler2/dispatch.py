from asyncio import FIRST_COMPLETED, CancelledError, create_task, sleep, wait
from logging import getLogger
from time import time
from typing import Awaitable, Callable, Optional
from uuid import uuid4

from typing_extensions import overload

import commons.task_typing
from commons.task_typing import (CompileResult, CompileTask, Input,
                                 JudgeResult, JudgeTask, Result, StatusUpdate,
                                 StatusUpdateDone, StatusUpdateError,
                                 StatusUpdateProgress, StatusUpdateStarted)
from commons.util import deserialize, serialize
from scheduler2.config import (redis, redis_queues,
                               task_concurrency_per_account, task_retries,
                               task_retry_interval_secs, task_timeout_secs)
from scheduler2.monitor import wait_until_offline
from scheduler2.util import (RateLimiter, RunnerOfflineException, TaskInfo,
                             taskinfo_from_task_id)

logger = getLogger(__name__)
classes = commons.task_typing.__dict__

rate_limiter = RateLimiter(task_concurrency_per_account)


@overload
async def run_task(
    taskinfo: TaskInfo[CompileTask],
    onprogress: Optional[Callable[[StatusUpdate], Awaitable]] = None,
    rate_limit_group: Optional[str] = None,
    retries_left: int = task_retries,
) -> CompileResult: pass
@overload
async def run_task(
    taskinfo: TaskInfo[JudgeTask[Input]],
    onprogress: Optional[Callable[[StatusUpdate], Awaitable]] = None,
    rate_limit_group: Optional[str] = None,
    retries_left: int = task_retries,
) -> JudgeResult: pass
async def run_task(taskinfo, onprogress = None, rate_limit_group = None,
                   retries_left = task_retries):
    task_id = str(uuid4())
    taskinfo.id = task_id
    task = taskinfo.task
    taskinfo_from_task_id[task_id] = taskinfo

    async def retry(msg):
        if retries_left <= 0:
            logger.warn(f'Task {task_id} failed: {msg}')
            raise Exception(msg)
        logger.info(f'Task {task_id} failed: {msg}, retrying')
        await sleep(task_retry_interval_secs)
        return await run_task(taskinfo, onprogress, rate_limit_group,
            retries_left - 1)

    try:
        async with rate_limiter.limit(rate_limit_group):
            logger.debug(f'running task {task_id}: {task}')

            queues = redis_queues.task(task_id)
            await redis.lpush(queues.task, serialize(task))
            await redis.expire(queues.task, task_timeout_secs)
            await redis.lpush(redis_queues.tasks_group(taskinfo.group), task_id)
            task_timeout = time() + task_timeout_secs

            offline_task = None
            try:
                while True:
                    progress_task = create_task(redis.brpop(queues.progress,
                        int(task_timeout - time())))
                    tasks = (progress_task,)
                    if offline_task is not None:
                        tasks = (progress_task, offline_task)
                    done, _ = await wait(tasks, return_when=FIRST_COMPLETED)
                    for done_task in done:
                        try:
                            res = await done_task
                        except RunnerOfflineException:
                            return await retry('Runner offline')
                    if res is None:
                        return await retry('Task timed out')
                    _, status = res
                    status: StatusUpdate = deserialize(status)  # type: ignore
                    logger.debug(f'received status update from task {task_id}: {status}')

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
                logger.info(f'aborting task {task_id}')
                await redis.lpush(queues.abort, 1)
                await redis.expire(queues.abort, task_timeout_secs)
                raise
    finally:
        del taskinfo_from_task_id[task_id]
