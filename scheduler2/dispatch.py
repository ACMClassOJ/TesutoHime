from asyncio import CancelledError, sleep
from dataclasses import dataclass
from logging import getLogger
from typing import Awaitable, Callable, Dict, Optional
from uuid import uuid4

import commons.task_typing
from commons.task_typing import (Result, StatusUpdate, StatusUpdateDone,
                                 StatusUpdateError, StatusUpdateProgress,
                                 StatusUpdateStarted, Task)
from commons.util import deserialize, serialize

from scheduler2.config import (redis_connect, redis_queues,
                               task_concurrency_per_account, task_retries,
                               task_retry_interval_secs, task_timeout_secs)
from scheduler2.util import RateLimiter

logger = getLogger(__name__)
redis = redis_connect()
classes = commons.task_typing.__dict__

rate_limiter = RateLimiter(task_concurrency_per_account)


@dataclass
class TaskInfo:
    task: Task
    submission_id: Optional[str]
    problem_id: str
    message: str
    id: str = ''

taskinfo_from_task_id: Dict[str, TaskInfo] = {}

async def run_task(
    taskinfo: TaskInfo,
    onprogress: Callable[[StatusUpdate], Awaitable] = None,
    rate_limit_group: Optional[str] = None,
    retries_left: int = task_retries,
) -> Result:
    task_id = str(uuid4())
    taskinfo.id = task_id
    task = taskinfo.task
    taskinfo_from_task_id[task_id] = taskinfo
    try:
        async with rate_limiter.limit(rate_limit_group):
            logger.debug(f'running task {task_id}: {task}')
            queues = redis_queues.task(task_id)
            await redis.lpush(queues.task, serialize(task))
            await redis.expire(queues.task, task_timeout_secs)
            await redis.lpush(redis_queues.tasks, task_id)
            try:
                while True:
                    _, status = await redis.blpop(queues.progress,
                        task_timeout_secs)
                    status: StatusUpdate = deserialize(status)
                    logger.debug(f'received status update from task {task_id}: {status}')
                    if isinstance(status, StatusUpdateStarted):
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
                        if retries_left <= 0:
                            raise Exception(msg)
                        await sleep(task_retry_interval_secs)
                        return await run_task(taskinfo, onprogress,
                            rate_limit_group, retries_left - 1)
                    else:
                        raise Exception(f'Unknown message from runner: {status}')
            except CancelledError:
                logger.info(f'aborting task {task_id}')
                await redis.lpush(queues.abort, 1)
                await redis.expire(queues.abort, task_timeout_secs)
                raise
    finally:
        del taskinfo_from_task_id[task_id]
