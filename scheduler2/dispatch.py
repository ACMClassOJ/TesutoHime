from asyncio import CancelledError, sleep
from logging import getLogger
from typing import Awaitable, Callable, Optional
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


async def run_task (
    task: Task,
    onprogress: Callable[[StatusUpdate], Awaitable] = None,
    rate_limit_group: Optional[str] = None,
    retries_left: int = task_retries,
) -> Result:
    async with rate_limiter.limit(rate_limit_group):
        task_id = str(uuid4())
        logger.debug(f'running task {task_id}: {task}')
        queues = redis_queues.task(task_id)
        await redis.set(queues.task, serialize(task))
        await redis.lpush(redis_queues.tasks, task_id)
        try:
            while True:
                _, status = await redis.blpop(queues.progress,
                    task_timeout_secs)
                status: StatusUpdate = deserialize(status)
                match status:
                    case StatusUpdateStarted():
                        if onprogress is not None:
                            await onprogress(status)
                    case StatusUpdateProgress():
                        if onprogress is not None:
                            await onprogress(status)
                    case StatusUpdateDone(result):
                        return result
                    case StatusUpdateError(message):
                        msg = f'Runner error: {message}'
                        logger.error(msg)
                        if retries_left <= 0:
                            raise Exception(msg)
                        await sleep(task_retry_interval_secs)
                        return await run_task(task, onprogress,
                            rate_limit_group, retries_left - 1)
                    case _:
                        raise Exception(f'Unknown message from runner: {status}')
        except CancelledError:
            logger.info(f'aborting task {task_id}')
            await redis.lpush(queues.abort, 1)
            raise
