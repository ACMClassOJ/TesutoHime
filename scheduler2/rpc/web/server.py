__all__ = ('app', )

from asyncio import CancelledError, Future, create_task, shield, wait
from dataclasses import asdict
from http.client import BAD_REQUEST
from logging import getLogger
from time import time
from typing import Dict, Optional
from urllib.parse import quote

from aiohttp.web import (Application, HTTPNotFound, Request, Response,
                         RouteTableDef, json_response)
from botocore.exceptions import ClientError

from commons.task_typing import (CodeLanguage, ProblemJudgeResult,
                                 SourceLocation)
from commons.util import deserialize, dump_dataclass, format_exc, serialize
from scheduler2.config import (plan_key, runner_heartbeat_interval_secs,
                               s3_buckets)
from scheduler2.plan import (InvalidCodeException, InvalidProblemException,
                             execute_plan, generate_plan, get_partial_result)
from scheduler2.plan.languages import languages_accepted
from scheduler2.plan.summary import summarize
from scheduler2.rpc.runner.client import get_runner_status
from scheduler2.rpc.web.client import make_request
from scheduler2.s3 import read_file, upload_str
from scheduler2.state.judge_tasks import JudgeTaskArgs, create_judge_task, judge_task_args, judge_task_from_submission_id, judge_tasks_from_problem_id

logger = getLogger(__name__)
routes = RouteTableDef()


@routes.post('/problem/{problem_id}/update')
async def update_problem(request: Request):
    problem_id = request.match_info['problem_id']
    task_args = []
    try:
        tasks = judge_tasks_from_problem_id(problem_id)
        for task in tasks:
            if not task.cancelled():
                task.cancel()
        task_args = [judge_task_args(x) for x in tasks]

        plan = await generate_plan(problem_id)
        languages = languages_accepted(plan)
        summary = dump_dataclass(summarize(plan))
        plan_str = serialize(plan)
        await upload_str(s3_buckets.problems, plan_key(problem_id), plan_str)
    except InvalidProblemException as e:
        return json_response({'result': 'invalid problem', 'error': str(e)})
    except Exception as e:
        err = format_exc(e)
        logger.error('error updating problem %(id)s: %(error)s', { 'id': problem_id, 'error': err }, 'plan:update')
        return json_response({'result': 'system error', 'error': err})
    finally:
        for task1 in task_args:
            create_judge_task(task1, run_judge)
    logger.info('plan for problem %(id)s updated', { 'id': problem_id }, 'plan:update')
    return json_response({'result': 'ok', 'error': None, 'languages': languages, 'summary': summary})


async def run_judge(args: JudgeTaskArgs):
    res = None
    logger.info('judging submission %(id)s for problem %(problem)s', { 'id': args.submission_id, 'problem': args.problem_id }, 'judge:start')
    try:
        plan_str = None
        try:
            plan_str = await read_file(s3_buckets.problems, plan_key(args.problem_id))
        except ClientError:
            msg = 'Cannot get judge plan'
            res = ProblemJudgeResult(result='bad_problem', message=msg)
        if plan_str is not None:
            plan = deserialize(plan_str)
            logger.debug('plan for problem %(id)s loaded', { 'id': args.problem_id }, 'plan:load')
            res = await execute_plan(plan, args)
    except CancelledError:
        if res is None:
            res = ProblemJudgeResult(result='aborted', message='Aborted')
    except ClientError as e:
        msg = f'Unknown error: {e}'
        res = ProblemJudgeResult(result='system_error', message=msg)
    except InvalidProblemException as e:
        logger.warning('invalid problem encountered in judging: %(error)s', { 'error': e }, 'judge:invalidproblem')
        if res is None:
            msg = f'Invalid problem: {e}'
            res = ProblemJudgeResult(result='bad_problem', message=msg)
    except InvalidCodeException as e:
        if res is None:
            msg = f'Invalid code: {e}'
            res = ProblemJudgeResult(result='compile_error', message=msg)
    except Exception as e:
        msg = f'Internal error: {format_exc(e)}'
        logger.error('error judging problem: %(message)s', { 'message': msg }, 'judge:error')
        if res is None:
            res = ProblemJudgeResult(result='system_error', message=msg)
    task = make_request(f'api/submission/{quote(args.submission_id)}/result', res)
    try:
        await shield(task)
    except CancelledError:
        pass


@routes.post('/judge')
async def judge(request: Request):
    try:
        body = await request.json()
        args = JudgeTaskArgs(
            problem_id       = body['problem_id'],
            submission_id    = body['submission_id'],
            language         = CodeLanguage(body['language']),
            source           = SourceLocation(**body['source']),
            rate_limit_group = body['rate_limit_group'],
        )

        create_judge_task(args, run_judge)
    except Exception as e:
        return json_response({'result': 'system error', 'error': format_exc(e)})
    return json_response({'result': 'ok', 'error': None})


@routes.get('/submission/{submission_id}/status')
async def get_status(request: Request):
    submission_id = request.match_info['submission_id']
    res = await get_partial_result(submission_id)
    if res is None:
        raise HTTPNotFound()
    return json_response(dump_dataclass(res))


@routes.post('/submission/{submission_id}/abort')
async def abort_judge(request: Request):
    submission_id = request.match_info['submission_id']
    try:
        task = judge_task_from_submission_id(submission_id)
    except KeyError:
        raise HTTPNotFound()
    if not task.cancelled():
        logger.info('aborting judge %(id)s', { 'id': submission_id }, 'judge:abort')
        task.cancel()
    return json_response({'result': 'ok', 'error': None})


cached_runner_status: Optional[Dict[str, dict]] = None
cached_runner_status_time: Optional[float] = None
runner_status_future: Optional[Future] = None

@routes.get('/status')
async def runner_status(request: Request):
    if not 'id' in request.query:
        return Response(text='no runner id specified', status=BAD_REQUEST)
    ids = request.query['id'].split(',')
    if len(ids) == 0:
        return Response(text='no runner id specified', status=BAD_REQUEST)
    global cached_runner_status
    global cached_runner_status_time
    global runner_status_future
    if cached_runner_status is not None:
        assert cached_runner_status_time is not None
        if time() - cached_runner_status_time > runner_heartbeat_interval_secs:
            cached_runner_status = None
            cached_runner_status_time = None
    if cached_runner_status is None:
        if runner_status_future is None:
            runner_status_future = Future()
            async def stat(id):
                return (id, asdict(await get_runner_status(id)))
            try:
                tasks = [create_task(stat(x)) for x in ids]
                tasks, _ = await wait(tasks)
                cached_runner_status = dict([await x for x in tasks])
                cached_runner_status_time = time()
                runner_status_future.set_result(cached_runner_status)
            except Exception as e:
                runner_status_future.set_exception(e)
            finally:
                runner_status_future = None
        else:
            await runner_status_future
    return json_response(cached_runner_status)


app = Application()
app.add_routes(routes)
