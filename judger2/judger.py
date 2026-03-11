import asyncio
import atexit
from collections import deque
from collections.abc import Callable, Coroutine
from dataclasses import field, dataclass
import functools
import json
from logging import getLogger
from time import time
from pydantic import validate_call
from typing import Any, NoReturn
from redis.asyncio import Redis

from commons.util import serialize
from judger2.cache import clean_cache_worker
from judger2.config import config


logger = getLogger(__name__)

type ProgressReporter = Callable[[Any], Coroutine[None, Any, None]]
type JudgerHandler[T] = Callable[[ProgressReporter, T, str], Coroutine[None, Any, None]]


@dataclass
class Judger:
    group_id: str = "default"
    task_handlers: dict[str, JudgerHandler[Any]] = field(
        default_factory=dict[str, JudgerHandler[Any]]
    )
    redis: Redis[str] = field(
        default_factory=lambda: Redis(
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=5,
            socket_keepalive=True,
            **config.redis.connection.model_dump(),
        ),
    )

    def register_task_handler[T](self, name: str, handler: JudgerHandler[T]):
        self.task_handlers[name] = validate_call(handler)

    async def send_heartbeats(self):
        while True:
            try:
                await self.redis.set(config.queues.heartbeat, time())
            except Exception as e:
                logger.error("error sending heartbeat: %(error)s", {"error": e}, "heartbeat")
            # put sleep outside the except block
            # make sure not attempting sending heartbeat too frequently
            await asyncio.sleep(config.task.heartbeat_interval_secs)

    async def _wait_cancel(self, task_id: str):
        while True:
            try:
                message = await self.redis.brpop(
                    config.queues.task(task_id).abort, timeout=config.task.poll_timeout_secs
                )
                if message is None:
                    continue
                return
            except Exception as e:
                logger.error("error processing signal: %(error)s", {"error": e}, "task:abortsignal")
                await asyncio.sleep(2)  # avoid busy loop when redis is unavailable

    async def report_progress(self, task_id: str, status: Any):
        """
        A wrapper for pushing status to redis.
        This method is provided for task handlers to report progress,
        so that they don't need to care about the detail of communication.
        """
        task_queues = config.queues.task(task_id)
        await self.redis.lpush(task_queues.progress, serialize(status))
        await self.redis.expire(task_queues.progress, config.task.timeout_secs)

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
                queue_id, task_id = await self.redis.brpop(queue_list, timeout=0)
                await self.redis.rpush(config.queues.in_progress, task_id)
                _, task_serialized = await self.redis.brpop(
                    config.queues.task(task_id).task, timeout=0
                )
                logger.info(f"received task {task_id} in queue {queue_id}")

                # dispatch task to handler
                handler = queue2handler[queue_id]
                reporter = functools.partial(self.report_progress, task_id)
                task = json.loads(task_serialized)
                works = [handler(reporter, task, task_id), self._wait_cancel(task_id)]

                # wait for task finish or cancel
                works = map(asyncio.create_task, works)
                done, pending = await asyncio.wait(works, return_when=asyncio.FIRST_COMPLETED)
                if pending:
                    for p in pending:
                        p.cancel()
                    res_cancels = await asyncio.gather(*pending, return_exceptions=True)
                    for res in res_cancels:
                        # Throw exception after cancel means bad design. Terminating.
                        # Note: Exception is not base class of CancelledError, so cancel is not counted here.
                        if isinstance(res, Exception):
                            raise res
                for p in done:
                    exc = p.exception()
                    if exc is not None:
                        logger.error(
                            "error occurred while processing task: %(error)s",
                            {"error": exc},
                            "task:process",
                        )
                        raise exc
                logger.info(f"finished task {task_id}")
            finally:
                if task_id is not None:
                    await self.redis.lrem(config.queues.in_progress, 0, task_id)

    async def online(self):
        logger.info("starting runner %(id)s", {"id": str(config.id)}, "runner:start")
        atexit.register(
            lambda: logger.info("runner %(id)s stopping", {"id": str(config.id)}, "runner:stop")
        )
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.send_heartbeats())
                tg.create_task(self.task_loop())
                tg.create_task(clean_cache_worker())
        except* (KeyboardInterrupt, asyncio.exceptions.CancelledError):
            logger.info(
                "runner %(id)s stopped by keyboard interrupt", {"id": str(config.id)}, "runner:stop"
            )
