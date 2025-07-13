from dataclasses import dataclass
from typing import Dict, Generic, Optional

from commons.task_typing import Task


@dataclass
class RunnerTaskInfo(Generic[Task]):
    task: Task
    submission_id: Optional[str]
    problem_id: str
    group: str
    message: str
    id: str = ''

_taskinfo_from_task_id: Dict[str, RunnerTaskInfo] = {}

def register_runner_task(taskinfo: RunnerTaskInfo):
    _taskinfo_from_task_id[taskinfo.id] = taskinfo

def deregister_runner_task(taskinfo: RunnerTaskInfo):
    del _taskinfo_from_task_id[taskinfo.id]

def runner_task_from_id(task_id: str) -> RunnerTaskInfo:
    return _taskinfo_from_task_id[task_id]
