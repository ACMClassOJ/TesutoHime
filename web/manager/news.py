__all__ = ('NewsManager',)

from http.client import OK

import requests

from web.cache import Cache
from web.config import NewsConfig

cache = Cache('news', 60, json=True)

class NewsManager:
    @staticmethod
    def get_news():
        cached = cache.get('')
        if cached is not None:
            return cached
        try:
            res = requests.get(NewsConfig.feed)
            if res.status_code == OK:
                news = res.json()
                # prevent ValueErrors from negative date
                # this would happen if the blog post did not specify a date.
                for item in news:
                    if item['date'] < 0:
                        item['date'] = 0
                cache.set('', news)
                return news
            return []
        except Exception:
            return []
