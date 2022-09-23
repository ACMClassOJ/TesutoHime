import datetime
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

import boto3
import redis
import requests
from botocore.config import Config
from commons.models import JudgeRecord2, JudgeStatus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import *

engine = create_engine(mysql_connection_string, pool_recycle=mysql_connection_pool_recycle)
SqlSession = sessionmaker(bind=engine)

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
    return engine.dialect.connect(database=mysql_database, autocommit=True)


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


def ping(url: str) -> bool:
    url = url + '/ping'
    for i in range(0, 3):
        try:
            ret = requests.get(url).content.decode()  # Fixme: trust self-signed SSL
            if ret == '0':
                return True
        except requests.exceptions.RequestException:
            pass
    return False

def key_from_submission_id(submission_id) -> str:
    return f'{submission_id}.code'

def schedule_judge2(problem_id, submission_id, language, username):
    task = {
        'problem_id': str(problem_id),
        'submission_id': str(submission_id),
        'language': language,
        'source': {
            'bucket': S3Config.Buckets.submissions,
            'key': key_from_submission_id(submission_id),
        },
        'rate_limit_group': username,
    }
    url = urljoin(SchedulerConfig.base_url, 'judge')
    try:
        res = requests.post(url, json=task).json()
        if res['result'] != 'ok':
            raise Exception(f'Scheduler error: {res["error"]}')
    except BaseException as e:
        with SqlSession() as db:
            rec: JudgeRecord2 = db \
                .query(JudgeRecord2) \
                .where(JudgeRecord2.id == submission_id) \
                .one()
            rec.status = JudgeStatus.system_error
            rec.message = str(e)
            rec.score = 0
            db.commit()


class NotFoundException(Exception): pass
def mark_void2(id):
    with SqlSession() as db:
        submission: JudgeRecord2 = db.query(JudgeRecord2).where(JudgeRecord2.id == id).one_or_none()
        if submission is None:
            raise NotFoundException()
        submission.details = None
        submission.status = JudgeStatus.void
        submission.message = 'Your judge result has been marked as void by an admin.'
        submission.score = 0
        db.commit()

def rejudge2(id):
    with SqlSession() as db:
        submission: JudgeRecord2 = db.query(JudgeRecord2).where(JudgeRecord2.id == id).one_or_none()
        if submission is None:
            raise NotFoundException()
        schedule_judge2(
            submission.problem_id,
            id,
            submission.language,
            submission.username,
        )

@dataclass
class JudgeStatusInfo:
    name: str
    color: str
    abbrev: Optional[str] = None
    badge_type: Optional[str] = None

judge_status_info = {
    'accepted': JudgeStatusInfo('Accepted', 'green', 'AC', 'success'),
    'wrong_answer': JudgeStatusInfo('Wrong Answer', 'red', 'WA', 'danger'),

    'compile_error': JudgeStatusInfo('Compile Error', 'yellow', 'CE', 'warning'),
    'runtime_error': JudgeStatusInfo('Runtime Error', 'red', 'RE', 'warning'),
    'time_limit_exceeded': JudgeStatusInfo('Time Limit Exceeded', 'orange', 'TLE', 'warning'),
    'memory_limit_exceeded': JudgeStatusInfo('Memory Limit Exceeded', 'orange', 'MLE', 'warning'),
    'disk_limit_exceeded': JudgeStatusInfo('Disk Limit Exceeded', 'purple', 'DLE', 'warning'),
    'memory_leak': JudgeStatusInfo('Memory Leak', 'purple', 'Leak', 'warning'),

    'pending': JudgeStatusInfo('Pending', 'gray-dark', 'Pending', 'secondary'),
    'compiling': JudgeStatusInfo('Compiling', 'blue', 'Compiling', 'info'),
    'judging': JudgeStatusInfo('Judging', 'blue', 'Judging', 'info'),
    'void': JudgeStatusInfo('Voided', 'brown', 'Void', 'warning'),
    'aborted': JudgeStatusInfo('Aborted', 'gray-dark', 'Aborted', 'secondary'),

    'skipped': JudgeStatusInfo('Skipped', 'black', 'Skip', 'secondary'),
    'system_error': JudgeStatusInfo('System Error', 'gray-dark', 'SE', 'default'),
    'unknown_error': JudgeStatusInfo('Unknown Error', 'gray-dark', 'UKE', 'default'),
}

language_info = {
    'cpp': 'C++',
    'git': 'Git',
    'verilog': 'Verilog',
    'quiz': 'Quiz',
    'git_java': 'Git (Java)',
}

@dataclass
class RunnerStatus:
    name: str
    color: str

runner_status_info = {
    'invalid': RunnerStatus('Invalid', 'black-50'),
    'idle': RunnerStatus('Idle', 'blue'),
    'offline': RunnerStatus('Offline', 'black-50'),
    'busy': RunnerStatus('Busy', 'orange'),
}
