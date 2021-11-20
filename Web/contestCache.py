from utils import *

class ContestCache:

    expire_time = 14

    def __init__(self):
        self.redis = redis_connect()
        self.prefix = RedisConfig.prefix + "ContestCache_"

    def get(self, contest_id: int):
        rst = self.redis.get(self.prefix + str(contest_id))
        return eval(rst) if rst != None else []

    def put(self, contest_id: int, data: list):
        self.redis.set(self.prefix + str(contest_id), str(data), ex = self.expire_time)

Contest_Cache = ContestCache()