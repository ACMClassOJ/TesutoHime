from asyncio import Semaphore
from logging import getLogger
from typing import Dict, Optional

from scheduler2.config import task_concurrency_per_account


logger = getLogger(__name__)


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

rate_limiter = RateLimiter(task_concurrency_per_account)
