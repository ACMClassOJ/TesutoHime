import asyncio
import json
import time

from cache import clean_cache_worker
from config import heartbeat_interval_secs, redis_connect, task_queue_key, \
                   in_progress_key, poll_timeout_secs, signals_key
from rpc import rpc
from task import run_task
from util import asyncrun


async def send_heartbeats ():
    while True:
        try:
            data = {'timestamp': time.time(), 'task': current_task}
            rpc('heartbeat', data)
        except Exception as e:
            print('Error sending heartbeat to web server:', e)
        asyncio.sleep(heartbeat_interval_secs)


current_task_id = None
current_task: asyncio.Task = None


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
            current_task = asyncio.create_task(run_task(task, task_id))
            current_task_id = task_id
            try:
                await current_task
            except asyncio.CancelledError:
                print(f'Task {task_id} was cancelled')
        except Exception as e:
            print('Error processing task:', e)
            time.sleep(2)
        finally:
            current_task = None
            current_task_id = None


async def poll_for_signals ():
    redis = await redis_connect()
    while True:
        try:
            message = await asyncrun(lambda: redis.blpop(signals_key, poll_timeout_secs))
            if message == None: return
            message = json.loads(message)
            cmd = message['cmd']
            if cmd == 'cancel':
                if message['id'] == current_task_id:
                    current_task.cancel()
            else:
                raise Exception(f'Unknown command {cmd}')
        except Exception as e:
            print('Error processing signal:', e)
            time.sleep(2)


async def main ():
    asyncio.create_task(send_heartbeats())
    asyncio.create_task(poll_for_tasks())
    asyncio.create_task(poll_for_signals())
    asyncio.create_task(clean_cache_worker())


if __name__ == '__main__':
    asyncio.run(main())
