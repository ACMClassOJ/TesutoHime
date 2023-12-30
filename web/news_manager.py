__all__ = ('NewsManager',)

import json
from http.client import OK

import requests

from web.config import NewsConfig
from web.utils import RedisConfig, redis_connect

expire_time = 30
redis = redis_connect()
key = RedisConfig.prefix + 'news'

class NewsManager:
    @staticmethod
    def get_news():
        cached = redis.get(key)
        if cached is not None:
            return json.loads(cached)
        try:
            res = requests.get(NewsConfig.feed)
            if res.status_code == OK:
                news = res.json()
                # prevent ValueErrors from negative date
                # this would happen if the blog post did not specify a date.
                for item in news:
                    if item['date'] < 0:
                        item['date'] = 0
                text = json.dumps(news, ensure_ascii=False)
                redis.set(key, text, ex=expire_time)
                return news
            return []
        except Exception:
            return []
