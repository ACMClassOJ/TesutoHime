from asyncio import AbstractEventLoop, create_task, new_event_loop
import json
from threading import Thread
from typing import Any, Callable
from commons.task_typing import CodeLanguage, ProblemJudgeResult, SourceLocation

import commons.task_typing
from commons.util import asyncrun, dump_dataclass, load_dataclass

from scheduler2.config import s3_buckets
from scheduler2.plan import execute_plan, generate_plan
from scheduler2.s3 import read_file, upload_obj


loop: AbstractEventLoop = None

def start_main_loop ():
    global loop
    loop = new_event_loop()
    loop.run_forever()

Thread(target=start_main_loop).start()


def plan_key (problem_id: str) -> str:
    return f'plans/{problem_id}.json'

async def update_problem (problem_id: str):
    plan = await generate_plan(problem_id)
    plan = json.dumps(dump_dataclass(plan))
    await upload_obj(s3_buckets.problems, plan_key(problem_id), plan)

async def judge (problem_id, submission_id, language, source, callback):
    plan = await read_file(s3_buckets.problems, plan_key(problem_id))
    plan = load_dataclass(json.loads(plan), commons.task_typing.__dict__)
    res = await execute_plan(plan, submission_id, language, source)
    await asyncrun(lambda: callback(res))

background_tasks = set()

def schedule_judge (problem_id: str, submission_id: str,
    language: CodeLanguage, source: SourceLocation,
    callback: Callable[[ProblemJudgeResult], Any]):
    def task ():
        t = create_task(judge(problem_id, submission_id, language, source,
            callback))
        background_tasks.add(t)
        t.add_done_callback(background_tasks.discard)
    loop.call_soon_threadsafe(task)
