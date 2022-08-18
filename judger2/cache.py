from dataclasses import dataclass
from datetime import datetime
from http.client import NOT_MODIFIED, OK
from os import path, stat, utime
from pathlib import PosixPath
from time import time
from urllib.parse import urlsplit
from uuid import uuid5, NAMESPACE_URL

from aiohttp import request

from judger2.config import cache_dir


@dataclass
class CachedFile:
    path: PosixPath = None
    filename: str = None


def cached_from_url (url: str) -> CachedFile:
    cache = CachedFile()
    key = urlsplit(url).path
    cache_id = str(uuid5(NAMESPACE_URL, key))
    cache.path = PosixPath(path.join(cache_dir, cache_id))
    cache.filename = PosixPath(key).name
    return cache


utc_time_format = '%a, %d %b %Y %H:%M:%S GMT'


async def ensure_cached (url: str) -> CachedFile:
    cache = cached_from_url(url)
    headers = {}
    try:
        mtime = stat(cache.path).st_mtime
        date = datetime.fromtimestamp(mtime)
        utc_string = date.strftime(utc_time_format)
        headers['If-Modified-Since'] = utc_string
    except FileNotFoundError:
        mtime = time()
    async with request('GET', url, headers=headers) as resp:
        if resp.status == NOT_MODIFIED:
            utime(cache.path, (time(), mtime))
            return cache
        if resp.status != OK:
            raise Exception('Unknown response status while fetching object:', resp.status)
        with open(cache.path, 'w') as f:
            async for data, _ in resp.content.iter_chunks():
                f.write(data)
        last_modified = datetime \
            .strptime(resp.headers['Last-Modified'], utc_time_format) \
            .timestamp()
        utime(cache.path, (time(), last_modified))
        return cache


async def upload (local_path: str, url: str) -> CachedFile:
    pass


async def clean_cache_worker ():
    # TODO
    pass
