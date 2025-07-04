from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from http.client import GONE, NOT_FOUND, REQUEST_TIMEOUT
from time import time
from typing import Optional
from urllib.parse import quote

from aiohttp import ClientSession, ClientTimeout
from aiohttp.http import SERVER_SOFTWARE

from commons.task_typing import StatusUpdate, TaskWithId
from commons.util import RedisQueues, deserialize, deserialize_from_dict, serialize, serialize_to_dict
from judger2.config import poll_timeout_secs, redis, task_timeout_secs

class AbortSignal(Enum):
    doAbort = auto()
    dontAbort = auto()

@dataclass
class RunnerInfo:
    id: str
    group: str

class BaseTransport(ABC):
    info: RunnerInfo

    def __init__(self, info: RunnerInfo) -> None:
        super().__init__()
        self.info = info

    @abstractmethod
    async def put_heartbeat(self) -> None: pass
    @abstractmethod
    async def delete_task(self) -> None: pass

    @abstractmethod
    async def get_task(self) -> Optional[TaskWithId]: pass
    @abstractmethod
    async def put_progress(self, task_id: str, progress: StatusUpdate) -> None: pass
    @abstractmethod
    async def poll_for_abort_signal(self, task_id: str) -> AbortSignal: pass


class RedisTransport(BaseTransport):
    def __init__(self, info: RunnerInfo, prefix: str) -> None:
        super().__init__(info)
        self.queues = RedisQueues(prefix, RedisQueues.RunnerInfo(info.id, info.group))

    async def put_heartbeat(self) -> None:
        await redis.set(self.queues.heartbeat, time())
    async def delete_task(self) -> None:
        await redis.delete(self.queues.in_progress)

    async def get_task(self) -> Optional[TaskWithId]:
        id = await redis.brpoplpush(
            self.queues.tasks,
            self.queues.in_progress,
            poll_timeout_secs,
        )
        if id is None: return None
        task_serialised = await redis.rpop(self.queues.task(id).task)
        if task_serialised is None:
            await self.delete_task()
            return None
        return deserialize(task_serialised)

    async def put_progress(self, task_id: str, progress: StatusUpdate) -> None:
        q = self.queues.task(task_id).progress
        await redis.lpush(q, serialize(progress))
        await redis.expire(q, task_timeout_secs)

    async def poll_for_abort_signal(self, task_id: str) -> AbortSignal:
        message = await redis.brpop(self.queues.task(task_id).abort)
        if message is None: return AbortSignal.dontAbort
        else:               return AbortSignal.doAbort


class HttpTransport(BaseTransport):
    _session: Optional[ClientSession]

    def __init__(self, info: RunnerInfo, base_url: str, authorization: Optional[str]) -> None:
        super().__init__(info)
        self.base_url = base_url
        self._authorization = authorization
        self._session = None

    def _sess(self) -> ClientSession:
        if self._session is None:
            self._session = ClientSession(base_url=self.base_url, raise_for_status=True)
            self._session.headers['User-Agent'] = SERVER_SOFTWARE + ' TesutoHime/1'
            self._session.headers['X-TesutoHime-Scheduler-Api'] = 'v1'
            if self._authorization:
                self._session.headers['Authorization'] = self._authorization
        return self._session

    async def put_heartbeat(self) -> None:
        await self._sess().put(f'runner/{quote(self.info.id)}/heartbeat')

    async def delete_task(self) -> None:
        await self._sess().delete(f'runner/{quote(self.info.id)}/task')

    async def get_task(self) -> Optional[TaskWithId]:
        payload = {
            'runner': self.info.__dict__,
        }
        timeout = ClientTimeout(total=poll_timeout_secs)
        async with self._sess().post(f'task', json=payload, timeout=timeout, raise_for_status=False) as resp:
            if resp.status == REQUEST_TIMEOUT:
                return None
            resp.raise_for_status()
            text = await resp.json()
            return deserialize_from_dict(text)

    async def put_progress(self, task_id: str, progress: StatusUpdate) -> None:
        payload = serialize_to_dict(progress)
        await self._sess().put(f'task/{quote(task_id)}/progress', json=payload)

    async def poll_for_abort_signal(self, task_id: str) -> AbortSignal:
        timeout = ClientTimeout(total=poll_timeout_secs)
        async with self._sess().head(f'task/{quote(task_id)}/poll', timeout=timeout, raise_for_status=False) as resp:
            if resp.status == GONE or resp.status == NOT_FOUND:
                return AbortSignal.doAbort
            resp.raise_for_status()
            return AbortSignal.dontAbort
