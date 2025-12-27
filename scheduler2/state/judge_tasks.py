
from asyncio import Task, create_task
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Coroutine, Dict, Set
from commons.task_typing import CodeLanguage, SourceLocation


@dataclass
class JudgeTaskArgs:
    problem_id: str
    submission_id: str
    language: CodeLanguage
    source: SourceLocation
    rate_limit_group: str

_judge_tasks_from_problem_id: Dict[str, Set[Task]] = defaultdict(set)
_judge_task_from_submission_id: Dict[str, Task] = {}
_judge_task_args: Dict[Task, JudgeTaskArgs] = {}

def create_judge_task(args: JudgeTaskArgs, run_judge: Callable[[JudgeTaskArgs], Coroutine]):
    if args.submission_id in _judge_task_from_submission_id:
        # raise Exception('already judging')
        # should not raise error, or the submission will temporarily be System Error
        return
    task = create_task(run_judge(args))
    _judge_tasks_from_problem_id[args.problem_id].add(task)
    _judge_task_from_submission_id[args.submission_id] = task
    _judge_task_args[task] = args
    def cleanup(_):
        _judge_tasks_from_problem_id[args.problem_id].remove(task)
        del _judge_task_from_submission_id[args.submission_id]
        del _judge_task_args[task]
    task.add_done_callback(cleanup)

def judge_tasks_from_problem_id(id: str) -> Set[Task]:
    return _judge_tasks_from_problem_id[id]

def judge_task_from_submission_id(id: str) -> Task:
    return _judge_task_from_submission_id[id]

def judge_task_args(task: Task) -> JudgeTaskArgs:
    return _judge_task_args[task]
