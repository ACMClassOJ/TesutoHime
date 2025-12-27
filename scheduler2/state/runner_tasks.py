from asyncio import Event, Queue, create_task, sleep
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Generic, Optional

from commons.task_typing import Task
from scheduler2.config import RunnerInfo, runner_info, task_confirm_delay_secs


@dataclass
class RunnerTaskInfo(Generic[Task]):
    task: Task
    submission_id: Optional[str]
    problem_id: str
    group: str
    message: str
    id: str = ''

    execution: Optional['ExecutionRecord'] = None
    abort_signal: Event = field(default_factory=Event)

@dataclass
class ExecutionRecord:
    task: RunnerTaskInfo
    runner: 'Runner'
    confirmed: bool = False
    done: bool = False
    abort_signal: Event = field(default_factory=Event)

_task_from_id: Dict[str, RunnerTaskInfo] = {}

def _reset_exec(exec: Optional[ExecutionRecord]):
    if exec is None: return
    exec.abort_signal.set()
    if exec.task.execution == exec:
        exec.task.execution = None

def register_runner_task(taskinfo: RunnerTaskInfo):
    _task_from_id[taskinfo.id] = taskinfo

def deregister_runner_task(taskinfo: RunnerTaskInfo):
    if taskinfo.execution:
        exec = taskinfo.execution
        exec.abort_signal.set()
        exec.done = True
    taskinfo.abort_signal.set()
    del _task_from_id[taskinfo.id]

def runner_task_from_id(task_id: str) -> RunnerTaskInfo:
    return _task_from_id[task_id]

def runner_from_task_id(task_id: str) -> 'Runner':
    exec = _task_from_id[task_id].execution
    if exec is None: raise KeyError('No runner is assigned')
    return exec.runner


_queues: Dict[str, Queue[RunnerTaskInfo]] = defaultdict(lambda: Queue())

def get_queue(group: str) -> Queue[RunnerTaskInfo]:
    return _queues[group]


@dataclass
class Runner:
    info: RunnerInfo
    last_heartbeat: Optional[datetime] = None
    execution: Optional[ExecutionRecord] = None
    offline: Event = field(default_factory=Event)

_runners: Dict[str, Runner] = { id: Runner(info) for id, info in runner_info.items() }

def runner_receive_heartbeat(runner_id: str):
    runner = _runners[runner_id]
    runner.last_heartbeat = datetime.now()
    runner.offline.clear()

def runner_offline(runner_id: str):
    return _runners[runner_id].offline

def runner_task_get(runner_id: str) -> Optional[RunnerTaskInfo]:
    exec = _runners[runner_id].execution
    if exec is None: return None
    return exec.task

async def _check_task_health(exec: ExecutionRecord):
    await sleep(task_confirm_delay_secs)
    if not exec.confirmed:
        _reset_exec(exec)

# TODO: move to client.py
def runner_task_assign(runner_id: str, taskinfo: RunnerTaskInfo):
    runner = _runners[runner_id]
    taskinfo = _task_from_id[taskinfo.id]
    _reset_exec(taskinfo.execution)
    exec = taskinfo.execution = ExecutionRecord(taskinfo, runner)
    runner.execution = exec
    create_task(_check_task_health(exec))

def runner_task_clear(runner_id: str):
    runner = _runners[runner_id]
    if runner.execution is None: return
    _reset_exec(runner.execution)
    runner.execution = None
