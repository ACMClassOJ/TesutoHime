from asyncio import Task, create_task, sleep
from dataclasses import dataclass
from logging import getLogger
from time import time
from typing import Dict, Literal, Optional
from commons.util import format_exc

from scheduler2.config import (redis_connect, redis_queues,
                               runner_heartbeat_interval_secs)
from scheduler2.util import RunnerOfflineException, taskinfo_from_task_id

logger = getLogger(__name__)
redis = redis_connect()


@dataclass
class RunnerStatus:
    status: Literal['invalid', 'idle', 'busy', 'offline']
    message: str
    last_seen: Optional[float]

async def get_runner_status(runner_id: str):
    heartbeat = None
    try:
        runner_queues = redis_queues.runner(runner_id)
        heartbeat = await redis.get(runner_queues.heartbeat)
        if heartbeat is not None:
            heartbeat = float(heartbeat)
        if heartbeat is None \
        or heartbeat < time() - runner_heartbeat_interval_secs * 2:
            return RunnerStatus('offline', 'Offline', heartbeat)

        task_ids = await redis.lrange(runner_queues.in_progress, 0, -1)
        if len(task_ids) == 0:
            status = 'idle'
            msg = 'Idle'
        elif len(task_ids) == 1:
            status = 'busy'
            task_id = task_ids[0]
            if not task_id in taskinfo_from_task_id:
                msg = 'Busy'
            else:
                taskinfo = taskinfo_from_task_id[task_id]
                msg = taskinfo.message
        else:
            status = 'invalid'
            msg = 'Multiple tasks are running on this runner'
        return RunnerStatus(status, msg, heartbeat)
    except BaseException as e:
        if not isinstance(heartbeat, float):
            heartbeat = None
        msg = f'Cannot get runner status: {format_exc(e)}'
        logger.warn(msg)
        return RunnerStatus('invalid', msg, heartbeat)


watch_tasks: Dict[str, Task] = {}

def wait_until_offline(runner_id: str):
    if runner_id in watch_tasks:
        return watch_tasks[runner_id]
    logger.debug(f'Polling runner {runner_id} for offline signal')
    async def task():
        key = redis_queues.runner(runner_id).heartbeat
        while True:
            await sleep(runner_heartbeat_interval_secs * 2)
            heartbeat = await redis.get(key)
            if heartbeat is None \
            or float(heartbeat) < time() - runner_heartbeat_interval_secs * 5:
                raise RunnerOfflineException('Runner is offline')
    t = create_task(task())
    watch_tasks[runner_id] = t
    def cleanup(_):
        try:
            t.exception()
        except BaseException:
            pass
        del watch_tasks[runner_id]
    t.add_done_callback(cleanup)
    return t
