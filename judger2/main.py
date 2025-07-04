__import__('judger2.logging_')

from asyncio import CancelledError, create_task, run, sleep, wait
from atexit import register
from logging import getLogger

from commons.task_typing import (StatusUpdateDone, StatusUpdateError,
                                 StatusUpdateStarted)

from judger2.cache import clean_cache_worker
from judger2.config import (heartbeat_interval_secs, rpc, runner_id)
from judger2.logging_ import task_logger
from judger2.rpc import AbortSignal
from judger2.task import run_task

logger = getLogger(__name__)


async def send_heartbeats():
    while True:
        try:
            await rpc.put_heartbeat()
        except CancelledError:
            return
        except Exception as e:
            logger.error('error sending heartbeat: %(error)s', { 'error': e }, 'heartbeat')
        await sleep(heartbeat_interval_secs)


async def poll_for_tasks():
    await rpc.delete_task()
    while True:
        task_id = None
        try:
            task_with_id = await rpc.get_task()
            if task_with_id is None: continue
            task = task_with_id.task
            task_id = task_with_id.id

            async def report_progress(status):
                logger.debug('reporting progress for task %(id)s: %(status)s', { 'id': task_id, 'status': status }, 'task:progress')
                assert task_id is not None  # make mypy happy
                await rpc.put_progress(task_id, status)

            await report_progress(StatusUpdateStarted(runner_id))
            aio_task = create_task(run_task(task, task_id))

            async def poll_for_abort_signal():
                while True:
                    try:
                        assert task_id is not None  # make mypy happy
                        signal = await rpc.poll_for_abort_signal(task_id)
                        if signal == AbortSignal.dontAbort: continue
                        aio_task.cancel()
                        return
                    except CancelledError:
                        return
                    except Exception as e:
                        logger.error('error processing signal: %(error)s', { 'error': e }, 'task:abortsignal')
                        await sleep(2)
            abort_task = create_task(poll_for_abort_signal())

            try:
                result = await aio_task
                abort_task.cancel()
                task_logger.debug('task %(id)s completed with %(result)s', { 'id': task_id, 'result': result }, 'task:complete')
                await report_progress(StatusUpdateDone(result))
            except CancelledError:
                abort_task.cancel()
                task_logger.info('task %(id)s was aborted', { 'id': task_id }, 'task:abort')
            normal_completion = True
        except CancelledError:
            normal_completion = False
            error = 'Aborted'
            return
        except Exception as e:
            normal_completion = False
            error = str(e)
            task_logger.error('error processing task: %(error)s', { 'error': e }, 'task:error')
            await sleep(2)
        finally:
            if task_id is not None:
                try:
                    await rpc.delete_task()
                except Exception as e:
                    task_logger.error('error removing task from queue: %(error)s', { 'error': e }, 'task:remove')
                if not normal_completion:  # type: ignore
                    try:
                        await report_progress(StatusUpdateError(error))  # type: ignore
                    except Exception as e:
                        task_logger.error('error sending nack: %(error)s', { 'error': e }, { 'task:nack' })


async def main():
    logger.info('runner %(id)s starting', { 'id': runner_id }, 'runner:start')
    register(lambda: logger.info('runner %(id)s stopping', { 'id': runner_id }, 'runner:stop'))
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
