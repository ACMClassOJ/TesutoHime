from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from http.client import SEE_OTHER, UNAUTHORIZED
from math import ceil, inf
from typing import Any, Iterable, List, NoReturn, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

import boto3
import redis
import sqlalchemy as sa
from botocore.config import Config
from flask import abort, g, jsonify, redirect, request, url_for
from sqlalchemy import Select, create_engine, select
from sqlalchemy.orm import Session as _Session
from sqlalchemy.orm import sessionmaker
from werkzeug.local import LocalProxy

from web.config import DatabaseConfig, RedisConfig, S3Config
from web.const import api_scopes_order, language_info

engine = create_engine(DatabaseConfig.url,
                       pool_recycle=DatabaseConfig.connection_pool_recycle)
SqlSession = sessionmaker(bind=engine)

cfg = Config(signature_version='s3v4')
s3_public = boto3.client('s3', **S3Config.Connections.public, config=cfg)  # type: ignore
s3_internal = boto3.client('s3', **S3Config.Connections.internal, config=cfg)  # type: ignore

db: _Session = LocalProxy(lambda: g.db)  # type: ignore

def generate_s3_public_url(*args, **kwargs):
    url = s3_public.generate_presigned_url(*args, **kwargs)
    url = urlsplit(url)
    url = urlunsplit(('', '', url.path, url.query, url.fragment))
    if url[0] == '/':
        url = url[1:]
    return urljoin(S3Config.public_url, url)


def redis_connect():
    return redis.StrictRedis(decode_responses=True, **RedisConfig.connection)  # type: ignore


def readable_date(time) -> str:
    if type(time) == int or type(time) == float:
        time = datetime.fromtimestamp(time)
    return time.strftime('%Y-%m-%d')

def readable_time(time) -> str:
    if type(time) == int or type(time) == float:
        time = datetime.fromtimestamp(time)
    return time.strftime('%Y-%m-%d %H:%M:%S')

def readable_time_minutes(time: datetime) -> str:
    return time.strftime('%Y-%m-%d %H:%M')

def readable_lang_v1(lang: int) -> str:
    # Get the readable language name.
    lang_str = {
        0: 'C++',
        1: 'Git',
        2: 'Verilog',
        3: 'Quiz',
    }
    if lang in lang_str:
        return lang_str[lang]
    return 'UNKNOWN'

def readable_lang(lang: str) -> str:
    return 'Unknown' if lang not in language_info \
            else language_info[lang].name

def min_max(seq, neg_is_inf: bool = False):
    l = [x if not neg_is_inf or x >= 0 else inf for x in seq]
    return min(l), max(l)

def is_api_call() -> bool:
    return request.path.startswith(url_for('web.api.index'))

def abort_json(code: int, message: str) -> NoReturn:
    resp = jsonify({ 'error': code, 'message': message })
    resp.status_code = code
    abort(resp)

def abort_converter(code: int, message: str = '') -> NoReturn:
    if is_api_call():
        abort_json(code, message)
    else:
        abort(code, message)

def not_logged_in() -> NoReturn:
    if is_api_call():
        abort_json(UNAUTHORIZED, 'access token is missing or invalid')
    else:
        abort(redirect(url_for('web.login', next=request.full_path), SEE_OTHER))

def require_logged_in(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return not_logged_in()
        return func(*args, **kwargs)
    return wrapped

def sort_scopes(scopes: Iterable[str]) -> List[str]:
    return sorted(scopes, key=lambda x: api_scopes_order.index(x))


def gen_page(cur_page: int, max_page: int):
    ret = []
    if cur_page > 2:
        ret.append(['<<', 1, 0])
    else:
        ret.append(['<<', 1, -1])  # -1 for disabled
    if cur_page != 1:
        ret.append(['<', cur_page - 1, 0])
    else:
        ret.append(['<', cur_page - 1, -1])  # -1 for disabled
    if max_page < 5:
        for i in range(1, max_page + 1):
            if i != cur_page:
                ret.append([str(i), i, 0])
            else:
                ret.append([str(i), i, 1])  # 1 for highlight
    else:
        if cur_page - 2 < 1:
            for i in range(1, 6):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        elif cur_page + 2 > max_page:
            for i in range(max_page - 4, max_page + 1):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        else:
            for i in range(cur_page - 2, cur_page + 3):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
    if cur_page < max_page:
        ret.append(['>', cur_page + 1, 0])
    else:
        ret.append(['>', cur_page + 1, -1])
    if cur_page < max_page - 1:
        ret.append(['>>', max_page, 0])
    else:
        ret.append(['>>', max_page, -1])
    return ret

def gen_page_for_problem_list(cur_page: int, max_page: int, latest_page_under_11000: int):
    return gen_page(cur_page, max_page) + [['#', latest_page_under_11000, 0]]


'''
Unified search system.

The following code implements a generic search and pagination.
To create a new search, subclass SearchDescriptor and pass the class as
the descriptor to paged_search_*. The methods of the class are search
filters. Calling the method with a query should return a SQLAlchemy
boolean expression. If the method's parameter is annotated with type
int, the argument will be converted to an integer before passing to the
method. Fields that begin with an underscore _ are not treated as
parameters; you can use these fields for custom purposes.
'''
class SearchDescriptor:
    # The model object, e.g. Problem
    __model__: Any
    # asc or desc
    __order__ = 'desc'

    @classmethod
    def __base_query__(cls):
        return select(cls.__model__)

    @classmethod
    def __order_phrase__(cls):
        if cls.__order__ == 'asc':
            return cls.__model__.id.asc()
        elif cls.__order__ == 'desc':
            return cls.__model__.id.desc()
        else:
            raise Exception(f'Unknown order {cls.__order__}')

def get_search_param(name: str) -> Optional[str]:
    arg = request.args.get(name)
    return None if arg == '' else arg

def get_search_param_int(name: str) -> Optional[int]:
    arg = request.args.get(name)
    return None if arg is None else int(arg)

def paged_search_make_query(descriptor) -> Select[Any]:
    fields = [x for x in dir(descriptor) if x[0] != '_']
    args = dict((field, get_search_param(field)) for field in fields)
    query = descriptor.__base_query__()

    for key, value in args.items():
        if value is not None:
            f = getattr(descriptor, key)
            types = list(f.__annotations__.values())
            if len(types) > 0 and types[0] is int:
                filter = f(int(value))
            else:
                filter = f(value)
            query = query.where(filter)

    return query

@dataclass
class LimitOffsetSearchResult:
    query: Select[Any]
    entities: List[Any]
    count: int
    page: int
    max_page: int

def paged_search_limitoffset(per_page: int, descriptor) -> LimitOffsetSearchResult:
    query = paged_search_make_query(descriptor)

    page = int(request.args.get('page', '1'))
    offset = (page - 1) * per_page
    order = descriptor.__order_phrase__()

    entities_query = query.order_by(order).limit(per_page).offset(offset)
    entities = list(db.scalars(entities_query).all())
    count = db.scalar(select(sa.func.count()).select_from(query))  # type: ignore
    assert count is not None
    max_page = ceil(count / per_page)

    return LimitOffsetSearchResult(query, entities, count, page, max_page)

@dataclass
class CursorSearchResult:
    entities: List[Any]
    cursor: Optional[int]

def paged_search_cursor(per_page: int, descriptor) -> CursorSearchResult:
    query = paged_search_make_query(descriptor)

    cursor_str = request.args.get('cursor')
    if cursor_str is not None:
        cursor = int(cursor_str)
        if descriptor.__order__ == 'asc':
            filter = descriptor.__model__.id >= cursor
        elif descriptor.__order__ == 'desc':
            filter = descriptor.__model__.id <= cursor
        else:
            raise Exception(f'Unknown order {descriptor.__order__}')
        query = query.where(filter)

    order = descriptor.__order_phrase__()
    query = query.order_by(order).limit(per_page + 1)
    entities = list(db.scalars(query).all())
    cursor = None if len(entities) != per_page + 1 else entities[-1].id  # type: ignore
    if len(entities) == per_page + 1:
        entities = entities[:-1]

    return CursorSearchResult(entities, cursor)
