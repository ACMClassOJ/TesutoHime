import json
from utils import *

class ContestCache:

    expire_time = 14

    def __init__(self):
        self.redis = redis_connect()
        self.prefix = RedisConfig.prefix + "ranking"

    def _key(self, type, id):
        return f'{self.prefix}-{type}-{id}'

    def get(self, type, contest_id: int):
        rst = self.redis.get(self._key(type, contest_id))
        return json.loads(rst) if rst != None else None

    def put(self, type, contest_id: int, data: list):
        self.redis.set(
            self._key(type, contest_id),
            json.dumps(data, ensure_ascii=False),
            ex = self.expire_time
        )

Contest_Cache = ContestCache()
