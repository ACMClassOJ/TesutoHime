__all__ = ('app', )

from asyncio import timeout
from base64 import b64decode
from http.client import NO_CONTENT
from logging import getLogger
from typing import Awaitable, Callable
from aiohttp.hdrs import AUTHORIZATION
from aiohttp.web import Application, HTTPBadRequest, HTTPForbidden, HTTPNotFound, HTTPUnauthorized, Request, Response, RouteTableDef, StreamResponse, json_response, middleware

from commons.util import dump_dataclass
from scheduler2.config import RunnerInfo, poll_timeout_secs, runner_info
from scheduler2.state.runner_tasks import get_queue, runner_from_task_id, runner_receive_heartbeat, runner_task_assign, runner_task_clear


logger = getLogger(__name__)
routes = RouteTableDef()

@middleware
async def auth_middleware(
    request: Request,
    handler: Callable[[Request], Awaitable[StreamResponse]]
) -> StreamResponse:
    api_version = request.headers.get('X-TesutoHime-Scheduler-Api')
    if api_version != 'v1':
        return HTTPBadRequest(reason='Client version mismatch')

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
    runner = runner_info.get(user)
    if runner is None or runner.key != key:
        raise HTTPUnauthorized(reason='Bad credentials')
    id_requested = request.match_info.get('runner_id')
    if id_requested is not None and id_requested != user:
        raise HTTPForbidden()
    task_id = request.match_info.get('task_id')
    if task_id is not None:
        try:
            task_runner = runner_from_task_id(task_id)
        except KeyError:
            raise HTTPNotFound()
        if task_runner.info.id != runner.id:
            raise HTTPForbidden()

    request['runner'] = runner

    return await handler(request)


@routes.put('/runner/{runner_id}/heartbeat')
async def heartbeat(req: Request):
    runner_id = req.match_info['runner_id']
    runner_receive_heartbeat(runner_id)
    return Response(status=NO_CONTENT)

@routes.delete('/runner/{runner_id}/task')
async def delete_task(req: Request):
    runner_id = req.match_info['runner_id']
    runner_task_clear(runner_id)
    return Response(status=NO_CONTENT)

@routes.post('/task')
async def get_task(req: Request):
    runner: RunnerInfo = req['runner']
    queue = get_queue(runner.group)
    try:
        async with timeout(poll_timeout_secs):
            taskinfo = await queue.get()
    except TimeoutError:
        return Response(status=NO_CONTENT)
    runner_task_assign(runner.id, taskinfo)
    return json_response(dump_dataclass(taskinfo.task))

@routes.post('/task/{task_id}/progress')
async def task_progress(req: Request):
    pass

@routes.get('/task/{task_id}/poll')
async def task_abort_signal(req: Request):
    pass

app = Application(middlewares=[auth_middleware])
app.add_routes(routes)
