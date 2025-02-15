from asyncio import Semaphore, sleep
from dataclasses import dataclass, is_dataclass
from http.client import OK
from logging import getLogger
from typing import Any, Dict, Optional, Type, TypeVar, Union
from urllib.parse import quote, urljoin

from aiohttp import request
from typing_extensions import Generic, Literal, get_args, get_origin

from commons.task_typing import Task
from commons.util import dump_dataclass
from scheduler2.config import (request_retries, request_retry_interval_secs,
                               web_auth, web_base_url)

logger = getLogger(__name__)


async def make_request(path, body):
    if isinstance(body, str):
        args: Dict[Any, Any] = {'data': body}
    else:
        args = {'json': dump_dataclass(body)}
    url = urljoin(web_base_url, path)
    headers = {'Authorization': web_auth}
    async def do_request():
        async with request('PUT', url, headers=headers, **args) as res:  # type: ignore
            if res.status != OK:
                raise Exception(f'{res.status}')
    interval = request_retry_interval_secs
    for i in range(request_retries):
        will_retry = i < request_retries - 1
        try:
            await do_request()
            return
        except Exception as e:
            msg = 'Error sending request to %(path)s: %(error)s'
            args = { 'path': path, 'error': e }
            if will_retry:
                msg += ', will retry in %(interval)s seconds'
                args['interval'] = interval
            logger.error(msg, args, 'request:fail')
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
    def limit(self, key: Optional[str]):
        if key is None:
            return RateLimiter.Unlimited()
        if key not in self.semaphores:
            logger.debug('creating rate limit group %(key)s', { 'key': key }, 'ratelimit:create')
            self.semaphores[key] = Semaphore(self.max)
        return self.semaphores[key]


@dataclass
class TaskInfo(Generic[Task]):
    task: Task
    submission_id: Optional[str]
    problem_id: str
    group: str
    message: str
    id: str = ''

taskinfo_from_task_id: Dict[str, TaskInfo] = {}


class RunnerOfflineException (Exception): pass


T = TypeVar('T')

def dataclass_from_json(obj, typ: Type[T]) -> T:
    if typ is int:
        return int(obj)  # type: ignore
    if typ is str:
        return str(obj)  # type: ignore
    if typ is bool:
        return bool(obj)  # type: ignore
    if get_origin(typ) is Union:
        for t in get_args(typ):
            try:
                return dataclass_from_json(obj, t)
            except: pass
        raise TypeError(f'Cannot cast {repr(obj)} into {repr(typ)}')
    if get_origin(typ) is Literal:
        if obj not in get_args(typ):
            raise TypeError(f'Cannot cast {repr(obj)} into {repr(typ)}')
        return obj
    if get_origin(typ) is Optional:
        if obj is None: return None  # type: ignore
        return dataclass_from_json(obj, get_args(typ)[0])
    if is_dataclass(typ):
        if not isinstance(obj, dict):
            raise TypeError(f'Cannot cast {repr(obj)} into {repr(typ)}')
        args = {}
        for k in obj:
            if k not in typ.__annotations__:
                raise KeyError(f'Garbage field {k} for type {typ}')
            args[k] = dataclass_from_json(obj[k], typ.__annotations__[k])
        return typ(**args)  # type: ignore

    raise TypeError('invalid type in dataclass_from_json')
