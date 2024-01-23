from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

import boto3
import redis
from botocore.config import Config
from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as _Session
from sqlalchemy.orm import sessionmaker
from werkzeug.local import LocalProxy

from web.config import DatabaseConfig, RedisConfig, S3Config
from web.const import language_info

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
    return redis.StrictRedis(host=RedisConfig.host, port=RedisConfig.port, password=RedisConfig.password, db=RedisConfig.db, decode_responses=True)


def readable_date(time) -> str:
    if type(time) == int or type(time) == float:
        time = datetime.fromtimestamp(time)
    return time.strftime('%Y-%m-%d')

def readable_time(time) -> str:
    if type(time) == int or type(time) == float:
        time = datetime.fromtimestamp(time)
    return time.strftime('%Y-%m-%d %H:%M:%S')

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

def regularize_string(raw_str: str) -> str:
    raw_str = raw_str.lower() # lower_case
    raw_str = raw_str.replace(' ', '') # eliminate the blank
    return raw_str


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
