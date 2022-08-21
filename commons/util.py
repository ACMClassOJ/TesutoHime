from asyncio import get_running_loop
from dataclasses import is_dataclass
from typing import Any, Callable, Dict, Type, TypeVar
import yaml


T = TypeVar('T')

async def asyncrun (func: Callable[[], T]) -> T:
    return await get_running_loop().run_in_executor(None, func)


def load_config (name: str, program_version: str) -> dict:
    filename = f'{name}_config.yml'
    with open(filename) as f:
        config = yaml.load(f, yaml.Loader)

    if not f'{name}_config' in config:
        raise Exception(f'Config file is not valid {name} config. Check your {filename}.')

    config_version = config[f'{name}_config']

    if config_version != program_version:
        raise Exception(f'{filename} has wrong version, has {config_version}, expecting {program_version}.')

    return config


def dump_dataclass (object: Any):
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

def load_dataclass (object, classes: Dict[str, Type]) -> Any:
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
    return ctor(**object['value'])
