import json
from collections import namedtuple
from urllib.parse import urljoin

from aiohttp import request

from judger2.config import runner_id, web_base_url, web_box


def box (data: dict) -> bytes:
    return web_box.encrypt(json.dumps(data, ensure_ascii=False).encode())

def unbox (data: bytes):
    return json.loads(web_box.decrypt(data), \
        object_hook=lambda dict: namedtuple('Tmp', dict.keys())(*dict.values()))

def api_url (path: str) -> str:
    return urljoin(web_base_url, f'api/runner/{path}')

async def rpc (path: str, args: dict):
    args['runner_id'] = runner_id
    async with request('POST', api_url(path), data=box(args)) as resp:
        return unbox(await resp.read())
