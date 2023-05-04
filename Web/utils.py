import datetime
import time
from urllib.parse import urljoin, urlsplit, urlparse, urlunsplit

import boto3
import redis
import requests
from botocore.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import *

engine = create_engine(mysql_connection_string, pool_recycle=mysql_connection_pool_recycle)
SqlSession = sessionmaker(bind=engine)

mysql_url = urlparse(mysql_connection_string)
mysql_database = mysql_url.path[1:]
mysql_password = mysql_url.netloc.split('@')[0].split(':')[1:]
if len(mysql_password) > 0:
    mysql_password = { 'password': mysql_password[0] }
else:
    mysql_password = {}

cfg = Config(signature_version='s3v4')
s3_public = boto3.client('s3', **S3Config.Connections.public, config=cfg)
s3_internal = boto3.client('s3', **S3Config.Connections.internal, config=cfg)

def generate_s3_public_url(*args, **kwargs):
    url = s3_public.generate_presigned_url(*args, **kwargs)
    url = urlsplit(url)
    url = urlunsplit(('', '', url.path, url.query, url.fragment))
    if url[0] == '/':
        url = url[1:]
    return urljoin(S3Config.public_url, url)


def db_connect():
    return engine.dialect.connect(database=mysql_database, autocommit=True, **mysql_password)


def redis_connect():
    return redis.StrictRedis(host=RedisConfig.host, port=RedisConfig.port, password=RedisConfig.password, db=RedisConfig.db, decode_responses=True)


def unix_nano() -> int:  # Integer Unix Nano
    return int(time.time())


def unix_nano_float() -> float:  # float point time in Second
    return time.time()


def readable_time(nano) -> str:
    return str(time.strftime("%b-%d-%Y %H:%M:%S", datetime.datetime.fromtimestamp(nano).timetuple()))


def regularize_string(raw_str: str) -> str:
    raw_str = raw_str.lower() # lower_case 
    raw_str = raw_str.replace(' ', '') # eliminate the blank
    return raw_str


def gen_page(cur_page: int, max_page: int, disable_jump_to_last: bool = False):
    ret = []
    if cur_page != 1:
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
    if cur_page < max_page and not disable_jump_to_last:
        ret.append(['>>', max_page, 0])
    else:
        ret.append(['>>', max_page, -1])
    return ret

def gen_page_for_problem_list(cur_page: int, max_page: int, latest_page_under_11000: int):
    ret = []
    if cur_page != 1:
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
    if cur_page < max_page:
        ret.append(['>>', max_page, 0])
    else:
        ret.append(['>>', max_page, -1])
    ret.append(['#',latest_page_under_11000, 0])
    return ret
