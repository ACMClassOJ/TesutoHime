__all__ = ('app', )

from base64 import b64decode
from logging import getLogger
from typing import Awaitable, Callable
from aiohttp.hdrs import AUTHORIZATION
from aiohttp.web import Application, HTTPForbidden, HTTPUnauthorized, Request, RouteTableDef, StreamResponse, middleware

from scheduler2.config import runner_info


logger = getLogger(__name__)
routes = RouteTableDef()

@middleware
async def auth_middleware(
    request: Request,
    handler: Callable[[Request], Awaitable[StreamResponse]]
) -> StreamResponse:
    authz = request.headers.get(AUTHORIZATION)
    if authz is None: raise HTTPUnauthorized(reason='Authorization header needed')
    try:
        method, payload = authz.split(' ')
    except ValueError:
        raise HTTPUnauthorized(reason='Cannot parse Authorization header')
    if method.lower() != 'basic': raise HTTPUnauthorized(reason='Basic auth needed')
    try:
        user, key = b64decode(payload).decode().split(':')
    except Exception:
        raise HTTPUnauthorized()
    runner = runner_info[user]
    if runner is None or runner.key != key:
        raise HTTPUnauthorized(reason='Bad credentials')
    id_requested = request.match_info.get('match_info')
    if id_requested is not None and id_requested != user:
        raise HTTPForbidden()

    return await handler(request)


@routes.put('/runner/{runner_id}/heartbeat')
async def heartbeat(req: Request):
    pass

app = Application(middlewares=[auth_middleware])
app.add_routes(routes)

