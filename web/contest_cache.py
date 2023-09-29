__all__ = ('ContestCache',)

import json

from web.utils import RedisConfig, redis_connect


class ContestCache:

    expire_time = 14
    redis = redis_connect()
    prefix = RedisConfig.prefix + 'ranking'

    @staticmethod
    def _key(type, id):
        return f'{ContestCache.prefix}-{type}-{id}'

    @staticmethod
    def get(type, contest_id: int):
        rst = ContestCache.redis.get(ContestCache._key(type, contest_id))
        return json.loads(rst) if rst != None else None

    @staticmethod
    def put(type, contest_id: int, data: list):
        ContestCache.redis.set(
            ContestCache._key(type, contest_id),
            json.dumps(data, ensure_ascii=False),
            ex = ContestCache.expire_time
        )
