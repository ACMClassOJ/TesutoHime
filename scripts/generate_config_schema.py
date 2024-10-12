'''
Generates JSON schema from dataclasses for problem config.json, and writes
to /web/static/assets/problem-config.schema.json.

Please run this script after modifying config.json format.
'''

import json
from dataclasses import MISSING, fields, is_dataclass
from types import NoneType
from typing import List, Optional, Union
from pathlib import PosixPath

from typing_extensions import Literal, get_args, get_origin

from scheduler2.problem_typing import ProblemConfig, SpjConfig, SpjNumeric


def schema(typ):
    if typ is int:
        return { 'type': 'integer' }
    if typ is float:
        return { 'type': 'number' }
    if typ is str:
        return { 'type': 'string' }
    if typ is bool:
        return { 'type': 'boolean' }
    if typ is None:
        return { 'type': 'null' }
    if get_origin(typ) is List or get_origin(typ) is list:
        return { 'type': 'array', 'items': schema(get_args(typ)[0]) }
    if get_origin(typ) is Literal:
        return { 'enum': get_args(typ) }
    if get_origin(typ) is Optional or (get_origin(typ) is Union and get_args(typ)[1] is NoneType and len(get_args(typ)) == 2):
        s = schema(get_args(typ)[0])
        if 'type' in s:
            s['type'] = [s['type'], 'null']
        elif 'anyOf' in s:
            s['anyOf'].append({ 'type': 'null' })
        elif 'enum' in s:
            s['enum'].append(None)
        else:
            assert False
        return s
    if get_origin(typ) is Union:
        return { 'anyOf': [schema(x) for x in get_args(typ)] }
    if is_dataclass(typ):
        props = {}
        required = []
        for f in fields(typ):
            if f.name == 'SPJ':
                s = schema(Union[SpjConfig, Literal.__getitem__(tuple(int(x) for x in SpjNumeric))])
            else:
                s = schema(f.type)
            if f.default != MISSING:
                s['default'] = f.default
            elif f.default_factory != MISSING:
                s['default'] = f.default_factory()
            elif f.name == 'SPJ':
                s['default'] = {}
            else:
                required.append(f.name)
            props[f.name] = s
        return { 'type': 'object', 'properties': props, 'required': required }

    print(typ)
    assert False

def problem_config_schema():
    s = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://acm.sjtu.edu.cn/OnlineJudge/static/assets/problem-config.schema.json',
        'title': 'ACMOJ Problem config.json',
    }
    s1 = schema(ProblemConfig)
    for k in s1:
        s[k] = s1[k]
    return s

def main():
    s = problem_config_schema()
    with open(PosixPath(__file__).parent.parent / 'web' / 'static' / 'assets' / 'problem-config.schema.json', 'w') as f:
        json.dump(s, f, indent=2)

if __name__ == '__main__':
    main()
