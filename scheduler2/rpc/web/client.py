from asyncio import sleep
from http.client import OK
from logging import getLogger
from typing import Any, Dict
from urllib.parse import quote, urljoin

from aiohttp import request

from commons.util import dump_dataclass
from scheduler2.config import request_retries, request_retry_interval_secs, web_auth, web_base_url


logger = getLogger(__name__)

async def make_request(path, body):
    if isinstance(body, str):
        args: Dict[Any, Any] = {'data': body}
    else:
        args = {'json': dump_dataclass(body)}
    url = urljoin(web_base_url, path)
    headers = {'Authorization': web_auth}
    async def do_request():
        async with request('PUT', url, headers=headers, **args) as res:
            if res.status != OK:
                raise Exception(f'{res.status}')
    interval = request_retry_interval_secs
    for i in range(request_retries):
        will_retry = i < request_retries - 1
        try:
            await do_request()
            return
        except Exception as e:
            msg = 'Error sending request to %(path)s: %(error)s'
            log_args = { 'path': path, 'error': e }
            if will_retry:
                msg += ', will retry in %(interval)s seconds'
                log_args['interval'] = interval
            logger.error(msg, log_args, 'request:fail')
            if not will_retry: raise
            await sleep(interval)
            interval *= 2

async def update_status(submission_id, status):
    return await make_request(f'api/submission/{quote(submission_id)}/status',
        status)
