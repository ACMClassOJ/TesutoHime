from asyncio import Semaphore, sleep
from dataclasses import dataclass
from http.client import OK
from logging import getLogger
from typing import Dict, Optional
from urllib.parse import quote, urljoin

from aiohttp import request

from commons.task_typing import Task
from commons.util import dump_dataclass
from scheduler2.config import (request_retries, request_retry_interval_secs,
                               web_auth, web_base_url)

logger = getLogger(__name__)


async def make_request(path, body):
    if isinstance(body, str) or isinstance(body, bytes):
        args = {'data': body}
    else:
        args = {'json': dump_dataclass(body)}
    url = urljoin(web_base_url, path)
    headers = {'Authorization': web_auth}
    async def do_request():
        async with request('PUT', url, headers=headers, **args) as res:
            if res.status != OK:
                raise Exception(f'{res.status}')
    interval = request_retry_interval_secs
    for i in range(request_retries):
        will_retry = i < request_retries - 1
        try:
            await do_request()
            return
        except Exception as e:
            msg = f'Error sending request to {path}: {e}'
            if will_retry:
                msg += f', will retry in {interval} seconds'
            logger.error(msg)
            if not will_retry: raise
            await sleep(interval)
            interval *= 2

async def update_status(submission_id, status):
    return await make_request(f'api/submission/{quote(submission_id)}/status',
        status)


class RateLimiter:
    max: int
    semaphores: Dict[str, Semaphore]
    def __init__(self, max: int):
        self.max = max
        self.semaphores = {}
    class Unlimited:
        async def __aenter__(self): pass
        async def __aexit__(self, *_): pass
    def limit(self, key: str):
        if key is None:
            return RateLimiter.Unlimited()
        if key not in self.semaphores:
            logger.debug(f'creating rate limit group {key}')
            self.semaphores[key] = Semaphore(self.max)
        return self.semaphores[key]


@dataclass
class TaskInfo:
    task: Task
    submission_id: Optional[str]
    problem_id: str
    group: str
    message: str
    id: str = ''

taskinfo_from_task_id: Dict[str, TaskInfo] = {}


class RunnerOfflineException (Exception): pass
