__import__('judger2.logging_')

from asyncio import CancelledError, create_task, run, sleep, wait
from atexit import register
from logging import getLogger
from time import time

from commons.task_typing import (StatusUpdateDone, StatusUpdateError,
                                 StatusUpdateStarted)
from commons.util import deserialize, format_exc, serialize

from judger2.cache import clean_cache_worker
from judger2.config import (heartbeat_interval_secs, poll_timeout_secs, queues,
                            redis, runner_id, task_timeout_secs)
from judger2.logging_ import task_logger
from judger2.task import run_task

logger = getLogger(__name__)


async def send_heartbeats():
    while True:
        try:
            await redis.set(queues.heartbeat, time())
        except CancelledError:
            return
        except Exception as e:
            logger.error(f'error sending heartbeat: {format_exc(e)}')
        await sleep(heartbeat_interval_secs)


async def poll_for_tasks():
    await redis.delete(queues.in_progress)
    while True:
        task_id = None
        try:
            task_id = await redis.brpoplpush(
                queues.tasks,
                queues.in_progress,
                poll_timeout_secs,
            )
            if task_id is None: continue
            task_queues = queues.task(task_id)
            async def report_progress(status):
                await redis.lpush(task_queues.progress, serialize(status))
                await redis.expire(task_queues.progress, task_timeout_secs)

            task_serialized = await redis.rpop(task_queues.task)
            if task_serialized is None:
                continue
            task = deserialize(task_serialized)
            aio_task = create_task(run_task(task, task_id))
            await report_progress(StatusUpdateStarted(runner_id))

            async def poll_for_abort_signal():
                while True:
                    try:
                        message = await redis.brpop(task_queues.abort,
                            poll_timeout_secs)
                        if message is None: continue
                        aio_task.cancel()
                        return
                    except CancelledError:
                        return
                    except Exception as e:
                        logger.error(f'Error processing signal: {format_exc(e)}')
                        await sleep(2)
            abort_task = create_task(poll_for_abort_signal())

            try:
                result = await aio_task
                abort_task.cancel()
                task_logger.debug(f'task {task_id} completed with {result}')
                await report_progress(StatusUpdateDone(result))
            except CancelledError:
                abort_task.cancel()
                task_logger.info(f'task {task_id} was aborted')
            normal_completion = True
        except CancelledError:
            normal_completion = False
            error = 'Aborted'
            return
        except Exception as e:
            normal_completion = False
            error = str(e)
            task_logger.error(f'error processing task: {format_exc(e)}')
            await sleep(2)
        finally:
            if task_id is not None:
                try:
                    await redis.lrem(queues.in_progress, 0, task_id)
                except Exception as e:
                    task_logger.error(f'error removing task from queue: {format_exc(e)}')
                if not normal_completion:
                    try:
                        await report_progress(StatusUpdateError(error))
                    except Exception as e:
                        task_logger.error(f'error sending nack: {format_exc(e)}')


async def main():
    logger.info(f'runner {runner_id} starting')
    register(lambda: logger.info(f'runner {runner_id} stopping'))
    await wait([
        create_task(send_heartbeats()),
        create_task(poll_for_tasks()),
        create_task(clean_cache_worker()),
    ])

if __name__ == '__main__':
    try:
        run(main())
    except KeyboardInterrupt:
        pass
