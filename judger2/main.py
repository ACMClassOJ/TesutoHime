__import__('judger2.logging_')

from asyncio import CancelledError, create_task, run, sleep, wait
from atexit import register
from json import dumps as dump_json
from json import loads as load_json
from logging import getLogger
from time import time
from traceback import print_exception

import commons.task_typing
from commons.util import dump_dataclass, load_dataclass

from judger2.cache import clean_cache_worker
from judger2.config import (heartbeat_interval_secs, poll_timeout_secs, queues,
                            redis_connect, runner_id)
from judger2.logging_ import task_logger
from judger2.task import run_task

logger = getLogger(__name__)


async def send_heartbeats ():
    redis = redis_connect()
    while True:
        try:
            await redis.set(queues.heartbeat, time())
        except CancelledError:
            return
        except BaseException as e:
            logger.error(f'error sending heartbeat: {e}')
        await sleep(heartbeat_interval_secs)


async def poll_for_tasks ():
    redis = redis_connect()
    await redis.delete(queues.in_progress)
    while True:
        task_id = None
        try:
            task_id = await redis.blmove(
                queues.tasks,
                queues.in_progress,
                poll_timeout_secs,
                'RIGHT',
                'LEFT',
            )
            if task_id is None: continue
            task_queues = queues.task(task_id)
            task = await redis.get(task_queues.task)
            task = load_dataclass(load_json(task), commons.task_typing.__dict__)
            aio_task = create_task(run_task(task, task_id))

            async def poll_for_abort_signal ():
                redis = redis_connect()
                while True:
                    try:
                        message = await redis.blpop(task_queues.abort,
                            poll_timeout_secs)
                        if message == None: continue
                        aio_task.cancel()
                        return
                    except Exception as e:
                        logger.error(f'Error processing signal: {e}')
                        await sleep(2)
            abort_task = create_task(poll_for_abort_signal())

            try:
                result = await aio_task
                abort_task.cancel()
                task_logger.debug(f'task {task_id} completed with {result}')
                await redis.set(task_queues.result,
                    dump_json(dump_dataclass(result)))
                await redis.lpush(task_queues.done, 1)
            except CancelledError:
                task_logger.info(f'task {task_id} was cancelled')
        except CancelledError:
            return
        except BaseException as e:
            task_logger.error(f'error processing task: {e}')
            print_exception(e)
            await sleep(2)
        finally:
            if task_id is not None:
                try:
                    await redis.lrem(queues.in_progress, 0, task_id)
                except BaseException as e:
                    task_logger.error(f'error removing task from queue: {e}')
                try:
                    await redis.lpush(task_queues.done, 0)
                except BaseException as e:
                    task_logger.error(f'error sending nack: {e}')


async def main ():
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
