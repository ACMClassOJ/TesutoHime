from asyncio import Semaphore
from http.client import OK
from logging import getLogger
from typing import Dict
from urllib.parse import quote, urljoin

from aiohttp import request
from commons.util import dump_dataclass

from scheduler2.config import web_auth, web_base_url

logger = getLogger(__name__)


async def make_request (path, body):
    if isinstance(body, str) or isinstance(body, bytes):
        args = {'data': body}
    else:
        args = {'json': dump_dataclass(body)}
    url = urljoin(web_base_url, path)
    headers = {'Authorization': web_auth}
    async with request('PUT', url, headers=headers, **args) as res:
        if res.status != OK:
            logger.error(f'Error sending request to {path}: {res.status}')

async def update_status (submission_id, status):
    return await make_request(f'api/submission/{quote(submission_id)}/status',
        status)


class RateLimiter:
    max: int
    semaphores: Dict[str, Semaphore]
    def __init__ (self, max: int):
        self.max = max
        self.semaphores = {}
    class Unlimited:
        async def __aenter__ (self): pass
        async def __aexit__ (self, *_): pass
    def limit (self, key: str):
        if key is None:
            return RateLimiter.Unlimited()
        if key not in self.semaphores:
            logger.debug(f'creating rate limit group {key}')
            self.semaphores[key] = Semaphore(self.max)
        return self.semaphores[key]
