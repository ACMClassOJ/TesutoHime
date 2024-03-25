import json
from typing import Any, Optional

from flask import g

from web.config import RedisConfig
from web.utils import redis_connect


class Cache:
    redis = redis_connect()
    prefix: str
    ttl: int
    json: bool

    def __init__(self, name: str, ttl_secs: int, *, json: bool = False) -> None:
        self.prefix = RedisConfig.prefix + name + ':'
        self.ttl = ttl_secs
        self.json = json

    def flush(self, key) -> None:
        key = self._key(key)
        if key in g.cache:
            del g.cache[key]
        self.redis.delete(key)

    def get(self, key) -> Optional[Any]:
        key = self._key(key)
        if key in g.cache:
            return g.cache[key]
        serialized = self.redis.get(key)
        deserialized = None if serialized is None else self._deserialize(serialized)
        g.cache[key] = deserialized
        return deserialized

    def set(self, key, value) -> None:
        key = self._key(key)
        g.cache[key] = value
        serialized = self._serialize(value)
        self.redis.set(key, serialized, ex=self.ttl)

    def hget(self, key, hash) -> Optional[Any]:
        key = self._key(key)
        if key not in g.cache:
            g.cache[key] = {}
        if hash in g.cache[key]:
            return g.cache[key][hash]
        serialized = self.redis.hget(key, hash)
        deserialized = None if serialized is None else self._deserialize(serialized)
        g.cache[key][hash] = deserialized
        return deserialized

    def hset(self, key, hash, value) -> None:
        key = self._key(key)
        if key not in g.cache:
            g.cache[key] = {}
        g.cache[hash] = value
        serialized = self._serialize(value)
        self.redis.hset(key, hash, serialized)
        self.redis.expire(key, self.ttl)

    def _serialize(self, value):
        if self.json:
            return json.dumps(value, ensure_ascii=False)
        return value

    def _deserialize(self, value):
        if self.json:
            return json.loads(value)
        return value

    def _key(self, key) -> str:
        return self.prefix + str(key)
