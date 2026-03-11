import asyncio
from logging import getLogger
from commons.task_typing import (
    CompileTask,
    Input,
    JudgeTask,
    StatusUpdateDone,
    StatusUpdateError,
    StatusUpdateStarted,
)
from judger2.config import config
from judger2.judger import Judger, ProgressReporter
from judger2.task import compile_task, judge_task

logger = getLogger(__name__)


async def default_task_handler(
    reporter: ProgressReporter, task: CompileTask | JudgeTask[Input], task_id: str
):
    try:
        await reporter(StatusUpdateStarted(str(config.id)))
        match task:
            case CompileTask():
                result = await compile_task(task)
            case JudgeTask():
                result = await judge_task(reporter, task)
            case _:
                assert False, "unreachable"
        await reporter(StatusUpdateDone(result))
    except Exception:
        await reporter(StatusUpdateError(str(config.id)))
        raise  # philosophy: termination is better than keeping silent


async def main():
    judger = Judger()
    judger.register_task_handler(config.group, default_task_handler)
    await judger.online()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
