from asyncio import CancelledError, sleep
from dataclasses import dataclass
from datetime import datetime, timezone
from http.client import NOT_MODIFIED, OK
from logging import getLogger
from os import chmod, path, remove, rename, scandir, stat, utime
from pathlib import PosixPath
from shutil import copy
from time import time
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from aiohttp import request

from judger2.config import (cache_clear_interval_secs, cache_dir,
                            cache_max_age_secs)

logger = getLogger(__name__)


@dataclass
class CachedFile:
    path: PosixPath
    filename: str


def cached_from_url(url: str) -> CachedFile:
    key = urlsplit(url).path
    cache_id = str(uuid5(NAMESPACE_URL, key))
    p = PosixPath(path.join(cache_dir, cache_id))
    filename = PosixPath(key).name
    return CachedFile(p, filename)


utc_time_format = '%a, %d %b %Y %H:%M:%S GMT'


async def ensure_cached(url: str) -> CachedFile:
    cache = cached_from_url(url)
    logger.debug('caching file %(filename)s to %(path)s', { 'filename': cache.filename, 'path': cache.path }, 'cache:ensure')
    headers = {}
    try:
        mtime = stat(cache.path).st_mtime
        date = datetime.fromtimestamp(mtime).astimezone(timezone.utc)
        utc_string = date.strftime(utc_time_format)
        headers['If-Modified-Since'] = utc_string
    except FileNotFoundError:
        mtime = time()
    async with request('GET', url, headers=headers) as resp:
        if resp.status == NOT_MODIFIED:
            logger.debug('%(filename)s is not modified, using cache', { 'filename': cache.filename, 'path': cache.path }, 'cache:hit')
            utime(cache.path, (time(), mtime))
            return cache
        if resp.status != OK:
            raise Exception(f'Unknown response status {resp.status} while fetching object')
        logger.debug('%(filename)s is modified, downloading file', { 'filename': cache.filename, 'path': cache.path }, 'cache:miss')
        part_path = cache.path.with_suffix('.part')
        try:
            with open(part_path, 'wb') as f:
                async for data, _ in resp.content.iter_chunks():
                    f.write(data)
            last_modified = datetime \
                .strptime(resp.headers['Last-Modified'], utc_time_format) \
                .replace(tzinfo=timezone.utc) \
                .timestamp()
            utime(part_path, (time(), last_modified))
            rename(part_path, cache.path)
        except CancelledError:
            try:
                remove(part_path)
            except Exception:
                pass
            raise
        return cache


async def upload(local_path: PosixPath, url: str) -> CachedFile:
    cache = cached_from_url(url)
    if not local_path.is_file() or local_path.is_symlink():
        raise ValueError('File to upload is not regular file')
    copy(local_path, cache.path)
    chmod(cache.path, 0o640)
    utime(cache.path)
    with open(cache.path, 'rb') as f:
        async with request('PUT', url, data=f) as resp:
            if resp.status != OK:
                raise Exception(f'Unknown response status {resp.status} while uploading file')
    return cache


def clear_cache():
    for file in scandir(cache_dir):
        if not file.is_file():
            continue
        st = file.stat()
        atime = max(st.st_atime, st.st_mtime)
        age = time() - atime
        if age > cache_max_age_secs:
            logger.debug('removing file %(path)s from cache as age is %(age)s', { 'path': file.path, 'age': age }, 'cache:purge')
            remove(file)

async def clean_cache_worker():
    while True:
        try:
            logger.info('clearing cache', {}, 'cache:clean')
            clear_cache()
        except CancelledError:
            return
        except Exception as e:
            logger.error('error while clearing cache: %(error)s', { 'error': e }, 'cache:clean')
        await sleep(cache_clear_interval_secs)
