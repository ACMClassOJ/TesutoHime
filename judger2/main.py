__import__("judger2.logging_")
import asyncio
from asyncio import CancelledError
from atexit import register
from logging import getLogger
from commons.task_typing import (
    CompileTask,
    Input,
    JudgeTask,
    StatusUpdate,
    StatusUpdateDone,
    StatusUpdateError,
    StatusUpdateStarted,
)
from commons.util import serialize
from judger2.config import config, redis
from judger2.judger import Judger
from judger2.logging_ import task_logger
from judger2.task import run_task

logger = getLogger(__name__)


async def default_task_handler(judger: Judger, task: CompileTask | JudgeTask[Input], task_id: str):
    async def report_progress(status: StatusUpdate):
        task_logger.debug(
            "reporting progress for task %(id)s: %(status)s",
            {"id": task_id, "status": status},
            "task:progress",
        )
        task_queues = config.queues.task(task_id)
        await redis.lpush(task_queues.progress, serialize(status))
        await redis.expire(task_queues.progress, config.task.timeout_secs)

    try:
        await report_progress(StatusUpdateStarted(str(config.id)))
        result = await run_task(task, task_id)
        await report_progress(StatusUpdateDone(result))
    except CancelledError:
        task_logger.info("task %(id)s cancelled", {"id": task_id}, "task:cancelled")
        await report_progress(StatusUpdateError(str(config.id)))


async def main():
    logger.info("runner %(id)s starting", {"id": str(config.id)}, "runner:start")
    register(lambda: logger.info("runner %(id)s stopping", {"id": str(config.id)}, "runner:stop"))
    judger = Judger()
    judger.register_task_handler(config.group, default_task_handler)
    await judger.online()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
