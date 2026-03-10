import asyncio
from collections import deque
from collections.abc import Callable, Coroutine
from dataclasses import field
import json
from logging import getLogger
from time import time
from pydantic import validate_call
from pydantic.dataclasses import dataclass
from typing import Any, NoReturn

from judger2.cache import clean_cache_worker
from judger2.config import redis, config

logger = getLogger(__name__)

# (judger, task, task_id) -> None
type JudgerHandler[T] = Callable[[Judger, T, str], Coroutine[None, Any, None]]


@dataclass
class Judger:
    group_id: str = "default"
    task_handlers: dict[str, JudgerHandler[Any]] = field(
        default_factory=dict[str, JudgerHandler[Any]]
    )

    def register_task_handler[T](self, name: str, handler: JudgerHandler[T]):
        self.task_handlers[name] = validate_call(handler)

    async def send_heartbeats(self):
        while True:
            try:
                await redis.set(config.queues.heartbeat, time())
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("error sending heartbeat: %(error)s", {"error": e}, "heartbeat")
            await asyncio.sleep(config.task.heartbeat_interval_secs)

    async def _wait_cancel(self, task_id: str):
        while True:
            try:
                message = await redis.brpop(
                    config.queues.task(task_id).abort, timeout=config.task.poll_timeout_secs
                )
                if message is None:
                    continue
                return
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("error processing signal: %(error)s", {"error": e}, "task:abortsignal")
                await asyncio.sleep(2)

    async def task_loop(self) -> NoReturn:
        queue_list = deque[str]()
        queue2handler: dict[str, JudgerHandler[Any]] = {}

        for name, handler in self.task_handlers.items():
            queue_name = f"{config.redis.prefix}-{name}-tasks"
            queue_list.append(queue_name)
            queue2handler[queue_name] = handler

        logger.info(f"listening for tasks in queues: {', '.join(queue_list)}")

        while True:
            task_id = None
            try:
                queue_list.rotate()  # fairness
                # start polling for tasks
                queue_id, task_id = await redis.brpop(queue_list, timeout=0)
                await redis.rpush(config.queues.in_progress, task_id)
                _, task_serialized = await redis.brpop(config.queues.task(task_id).task, timeout=0)
                logger.info(f"received task {task_id} in queue {queue_id}")

                # dispatch task to handler
                handler = queue2handler[queue_id]
                task = json.loads(task_serialized)
                works = [handler(self, task, task_id), self._wait_cancel(task_id)]
                # wait for task finish or cancel
                works = map(asyncio.create_task, works)
                done, pending = await asyncio.wait(works, return_when=asyncio.FIRST_COMPLETED)
                for p in pending:
                    p.cancel()
                for p in done:
                    exc = p.exception()
                    if exc is not None:
                        logger.error("error occurred while processing task: %(error)s", {"error": exc}, "task:process")
                        raise exc
                logger.info(f"finished task {task_id}")
            finally:
                if task_id is not None:
                    await redis.lrem(config.queues.in_progress, 0, task_id)

    async def online(self):
        logger.info("starting judger")
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.send_heartbeats())
                tg.create_task(self.task_loop())
                tg.create_task(clean_cache_worker())
        except* (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            logger.info("judger stopped by keyboard interrupt")
