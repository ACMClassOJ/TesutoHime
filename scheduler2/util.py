from dataclasses import is_dataclass
from logging import getLogger
from typing import Optional, Type, TypeVar, Union

from typing_extensions import Literal, get_args, get_origin


logger = getLogger(__name__)


T = TypeVar('T')

def dataclass_from_json(obj, typ: Type[T]) -> T:
    if typ is int:
        return int(obj)  # type: ignore
    if typ is str:
        return str(obj)  # type: ignore
    if typ is bool:
        return bool(obj)  # type: ignore
    if get_origin(typ) is Union:
        for t in get_args(typ):
            try:
                return dataclass_from_json(obj, t)
            except: pass
        raise TypeError(f'Cannot cast {repr(obj)} into {repr(typ)}')
    if get_origin(typ) is Literal:
        if obj not in get_args(typ):
            raise TypeError(f'Cannot cast {repr(obj)} into {repr(typ)}')
        return obj
    if get_origin(typ) is Optional:
        if obj is None: return None  # type: ignore
        return dataclass_from_json(obj, get_args(typ)[0])
    if is_dataclass(typ):
        if not isinstance(obj, dict):
            raise TypeError(f'Cannot cast {repr(obj)} into {repr(typ)}')
        args = {}
        for k in obj:
            if k not in typ.__annotations__:
                raise KeyError(f'Garbage field {k} for type {typ}')
            args[k] = dataclass_from_json(obj[k], typ.__annotations__[k])
        return typ(**args)  # type: ignore

    raise TypeError('invalid type in dataclass_from_json')
