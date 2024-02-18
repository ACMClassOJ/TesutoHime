__all__ = ('ContestCache',)

import json

from web.utils import RedisConfig, redis_connect


class ContestCache:
    expire_time = 14
    redis = redis_connect()
    prefix = RedisConfig.prefix + 'ranking:'

    @staticmethod
    def _key(id):
        return f'{ContestCache.prefix}-{id}'

    @classmethod
    def get(cls, contest_id: int):
        rst = cls.redis.get(cls._key(contest_id))
        return json.loads(rst) if rst is not None else None

    @classmethod
    def put(cls, contest_id: int, data: list):
        cls.redis.set(
            cls._key(contest_id),
            json.dumps(data, ensure_ascii=False),
            ex = cls.expire_time
        )

    @classmethod
    def flush(cls, contest_id: int):
        cls.redis.delete(cls._key(contest_id))
