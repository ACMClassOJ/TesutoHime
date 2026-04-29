from asyncio import CancelledError, Task, create_task, sleep
from logging import getLogger
from typing import Set

from prometheus_client import Counter, Gauge, Histogram

from scheduler2.config import runner_heartbeat_interval_secs

logger = getLogger(__name__)

# Counters
judge_requests_total = Counter(
    'scheduler_judge_requests_total',
    'Total judge requests received',
    ['language'],
)
judge_completed_total = Counter(
    'scheduler_judge_completed_total',
    'Total completed judge requests',
    ['result', 'language'],
)
tasks_retried_total = Counter(
    'scheduler_tasks_retried_total',
    'Total task retries',
    ['reason'],
)

# Histogram
judge_duration_seconds = Histogram(
    'scheduler_judge_duration_seconds',
    'Time spent judging a submission',
    ['language'],
)

# Gauges with callback (collected on scrape)
active_judges = Gauge(
    'scheduler_active_judges',
    'Number of currently active judge tasks',
)
active_tasks = Gauge(
    'scheduler_active_tasks',
    'Number of currently dispatched tasks',
)

# Task state gauge (incremented/decremented in dispatch.py)
tasks_by_state = Gauge(
    'scheduler_tasks_by_state',
    'Tasks by state',
    ['state'],
)

def _count_active_judges():
    from scheduler2.main import judge_tasks_from_submission_id
    return len(judge_tasks_from_submission_id)

def _count_active_tasks():
    from scheduler2.util import taskinfo_from_task_id
    return len(taskinfo_from_task_id)

active_judges.set_function(_count_active_judges)
active_tasks.set_function(_count_active_tasks)

# Runner status gauges (updated by background task)
runner_online = Gauge(
    'scheduler_runner_online',
    'Whether a runner is online (1) or not (0)',
    ['runner_id'],
)
runner_status = Gauge(
    'scheduler_runner_status_info',
    'Runner status as a labeled info gauge (1 = active status)',
    ['runner_id', 'status'],
)

seen_runners: Set[str] = set()
_runner_poll_task: Task | None = None


def observe_runner(runner_id: str):
    """Track a runner ID for status polling."""
    seen_runners.add(runner_id)


async def _poll_runner_statuses():
    from scheduler2.monitor import get_runner_status
    while True:
        for runner_id in list(seen_runners):
            try:
                status = await get_runner_status(runner_id)
                is_online = 1 if status.status != 'offline' else 0
                runner_online.labels(runner_id=runner_id).set(is_online)
                for s in ('idle', 'busy', 'invalid', 'offline'):
                    runner_status.labels(runner_id=runner_id, status=s).set(
                        1 if status.status == s else 0
                    )
            except Exception:
                pass
        await sleep(runner_heartbeat_interval_secs)


async def start_metrics(app):
    global _runner_poll_task
    _runner_poll_task = create_task(_poll_runner_statuses())
    logger.info('metrics background task started', {}, 'metrics:start')


async def stop_metrics(app):
    global _runner_poll_task
    if _runner_poll_task is not None:
        _runner_poll_task.cancel()
        try:
            await _runner_poll_task
        except CancelledError:
            pass
        _runner_poll_task = None
    logger.info('metrics background task stopped', {}, 'metrics:stop')
