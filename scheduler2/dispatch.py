from asyncio import CancelledError
from json import dumps as dump_json
from json import loads as load_json
from logging import getLogger
from uuid import uuid4

import commons.task_typing
from commons.task_typing import Result, Task
from commons.util import dump_dataclass, load_dataclass

from scheduler2.config import redis_connect, redis_queues, task_timeout_secs

logger = getLogger(__name__)
redis = redis_connect()


async def run_task (task: Task) -> Result:
    # TODO: rate limiting based on user
    # TODO: automatic retrying on failure
    task_id = str(uuid4())
    logger.debug(f'running task {task_id}: {task}')
    payload = dump_json(dump_dataclass(task))
    queues = redis_queues.task(task_id)
    try:
        await redis.set(queues.task, payload)
        await redis.lpush(redis_queues.tasks, task_id)
        try:
            # TODO: detect partial progress reports
            _, res = await redis.blpop(queues.done, task_timeout_secs)
            if res != '1':
                raise Exception('runner error')
        except CancelledError:
            await redis.lpush(queues.abort, 1)
            raise
        res = await redis.get(queues.result)
        if res is None:
            raise Exception('Task done without result')
        return load_dataclass(load_json(res), commons.task_typing.__dict__)
    finally:
        await redis.delete(queues.task, queues.result)
