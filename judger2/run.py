from judger2.logging_ import task_logger

from asyncio import CancelledError, Task, create_task, run, sleep, wait
from json import loads as load_json
from logging import getLogger
from time import time

from judger2.cache import clean_cache_worker
from judger2.config import heartbeat_interval_secs, redis_connect, task_queue_key, \
                   in_progress_key, poll_timeout_secs, signals_key, runner_id
from judger2.rpc import rpc
from judger2.task import run_task
from judger2.util import asyncrun

logger = getLogger(__name__)


async def send_heartbeats ():
    while True:
        try:
            data = {'timestamp': time(), 'task': current_task}
            await rpc('heartbeat', data)
        except Exception as e:
            logger.error(f'error sending heartbeat to web server: {e}')
        await sleep(heartbeat_interval_secs)


current_task_id = None
current_task: Task = None


async def poll_for_tasks ():
    redis = await redis_connect()
    while True:
        try:
            task_id = await asyncrun(lambda: redis.blmove(
                task_queue_key,
                in_progress_key,
                poll_timeout_secs,
                'RIGHT',
                'LEFT',
            ))
            if task_id == None: return
            task = await rpc('task', {'id': task_id})
            global current_task, current_task_id
            current_task = create_task(run_task(task, task_id))
            current_task_id = task_id
            try:
                await current_task
            except CancelledError:
                task_logger.info(f'task {task_id} was cancelled')
        except Exception as e:
            task_logger.error(f'error processing task: {e}')
            await sleep(2)
        finally:
            current_task = None
            current_task_id = None


async def poll_for_signals ():
    redis = await redis_connect()
    while True:
        try:
            message = await asyncrun(lambda: redis.blpop(signals_key, poll_timeout_secs))
            if message == None: return
            logger.info(f'received message {message}')
            message = load_json(message)
            cmd = message['cmd']
            if cmd == 'cancel':
                id = message['id']
                logger.info(f'received command to cancel {id}, {current_task_id=}')
                if id == current_task_id:
                    current_task.cancel()
            else:
                raise Exception(f'Unknown command {cmd}')
        except Exception as e:
            logger.error(f'Error processing signal: {e}')
            await sleep(2)


async def main ():
    logger.info(f'runner {runner_id} starting')
    await wait([
        create_task(send_heartbeats()),
        create_task(poll_for_tasks()),
        create_task(poll_for_signals()),
        create_task(clean_cache_worker()),
    ])


if __name__ == '__main__':
    try:
        run(main())
    except KeyboardInterrupt:
        pass
