import json
from asyncio import get_running_loop
from dataclasses import is_dataclass
from logging import getLogger
from pathlib import PosixPath
from shutil import rmtree
from traceback import format_exception
from typing import Any, Callable, Dict, Type, TypeVar
from uuid import uuid4

import yaml

import commons.task_typing

logger = getLogger(__name__)


T = TypeVar('T')

async def asyncrun(func: Callable[[], T]) -> T:
    return await get_running_loop().run_in_executor(None, func)


def load_config(name: str, program_version: str) -> dict:
    filename = f'{name}.yml'
    with open(filename) as f:
        config = yaml.safe_load(f)

    if not f'{name}_config' in config:
        raise Exception(f'Config file is not valid {name} config. Check your {filename}.')

    config_version = config[f'{name}_config']

    if config_version != program_version:
        raise Exception(f'{filename} has wrong version, has {config_version}, expecting {program_version}.')

    return config


def dump_dataclass(object: Any):
    if isinstance(object, int) \
    or isinstance(object, str) \
    or isinstance(object, float) \
    or isinstance(object, bool) \
    or object is None:
        return object
    if isinstance(object, list):
        return list(map(dump_dataclass, object))
    if not is_dataclass(object):
        raise ValueError('Only dataclasses could be dumped')
    return {
        'type': object.__class__.__name__,
        'value': dict(map(lambda e: (e[0], dump_dataclass(e[1])), \
            object.__dict__.items())),
    }

def serialize(object: Any) -> str:
    return json.dumps(dump_dataclass(object))


def load_dataclass(object, classes: Dict[str, Type]) -> Any:
    if isinstance(object, int) \
    or isinstance(object, str) \
    or isinstance(object, float) \
    or isinstance(object, bool) \
    or object is None:
        return object
    if isinstance(object, list):
        return list(map(lambda obj: load_dataclass(obj, classes), object))
    if not isinstance(object, dict):
        raise ValueError('invalid dump')
    ctor = classes[object['type']]
    values = dict(map(lambda e: (e[0], load_dataclass(e[1], classes)), \
        object['value'].items()))
    return ctor(**values)

def deserialize(data: str) -> Any:
    classes = commons.task_typing.__dict__
    return load_dataclass(json.loads(data), classes)


working_dir = None
before_exit = None

class TempDir:
    path: PosixPath
    def __init__(self):
        if working_dir is None:
            raise ValueError('TempDir is not initialized')
        self.path = PosixPath(working_dir) / str(uuid4())
    def __enter__(self) -> PosixPath:
        logger.debug(f'entering temp dir {self.path}')
        self.path.mkdir()
        self.path.chmod(0o770)
        return self.path
    def __exit__(self, *_args):
        logger.debug(f'exiting temp dir {self.path}')
        try:
            if before_exit is not None:
                before_exit(self.path)
            rmtree(self.path, ignore_errors=True)
        except Exception as e:
            logger.error(f'error removing temp dir {self.path}: {e}')

    @staticmethod
    def config(_working_dir, _before_exit = None):
        global working_dir, before_exit
        working_dir = _working_dir
        before_exit = _before_exit


class RedisQueues:
    def __init__(self, prefix: str, id: str = None):
        def queue(name):
            return f'{prefix}-{name}'
        def rqueue(name):
            return f'{queue(name)}-runner{id}'
        self.tasks = queue('tasks')
        self._prefix = prefix
        self._task_prefix = queue('task')
        if id is not None:
            self.in_progress = rqueue('in-progress')
            self.heartbeat = rqueue('heartbeat')

    class TaskRedisQueues:
        def __init__(self, prefix, id):
            def queue(name):
                return f'{prefix}-{name}-{id}'
            self.task = queue('task')
            self.progress = queue('progress')
            self.abort = queue('abort')
    def task(self, task_id: str) -> TaskRedisQueues:
        return RedisQueues.TaskRedisQueues(self._task_prefix, task_id)

    def with_id(self, runner_id: str):
        return RedisQueues(self._prefix, runner_id)


def format_exc(e):
    return format_exception(e, e, e.__traceback__)
