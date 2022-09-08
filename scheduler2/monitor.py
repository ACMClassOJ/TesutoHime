from dataclasses import dataclass
from time import time
from typing import Literal, Optional

from scheduler2.config import (redis_connect, redis_queues,
                               runner_heartbeat_interval_secs)
from scheduler2.dispatch import taskinfo_from_task_id

redis = redis_connect()


@dataclass
class RunnerStatus:
    status: Literal['invalid', 'idle', 'busy', 'offline']
    message: str
    last_seen: Optional[float]

async def get_runner_status (runner_id: str):
    heartbeat = None
    try:
        runner_queues = redis_queues.with_id(runner_id)
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
        msg = f'Cannot get runner status: {e}'
        return RunnerStatus('invalid', msg, heartbeat)
