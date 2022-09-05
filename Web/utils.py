from dataclasses import dataclass
import datetime
import time
from typing import Optional
from urllib.parse import urljoin

import boto3
import redis
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from commons.models import JudgeRecord2, JudgeStatus

from config import *

engine = create_engine(mysql_connection_string)
Session = sessionmaker(bind=engine)

s3 = boto3.client('s3', **S3Config.connection)


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


def gen_page(cur_page: int, max_page: int):
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

def key_from_submission_id (submission_id) -> str:
    return f'{submission_id}.code'

def schedule_judge2 (problem_id, submission_id, language, username):
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
        with Session() as db:
            rec: JudgeRecord2 = db \
                .query(JudgeRecord2) \
                .where(JudgeRecord2.id == submission_id) \
                .one()
            rec.status = JudgeStatus.system_error
            rec.message = str(e)
            db.commit()

@dataclass
class JudgeStatusInfo:
    name: str
    color: str
    abbrev: Optional[str] = None
    badge_type: Optional[str] = None

judge_status_info = {
    'pending': JudgeStatusInfo('Pending', 'gray-dark', 'Pending', 'secondary'),
    # TODO: update dark mode
    'compiling': JudgeStatusInfo('Compiling', 'blue', 'Compiling', 'info'),
    'judging': JudgeStatusInfo('Judging', 'blue', 'Judging', 'info'),
    # TODO: add the brown color to the stylesheets
    'void': JudgeStatusInfo('Voided', 'brown', 'Void', 'warning'),
    'aborted': JudgeStatusInfo('Aborted', 'gray-dark', 'Aborted', 'secondary'),

    'compile_error': JudgeStatusInfo('Compile Error', 'yellow', 'CE', 'warning'),
    'runtime_error': JudgeStatusInfo('Runtime Error', 'red', 'RE', 'warning'),
    'time_limit_exceeded': JudgeStatusInfo('Time Limit Exceeded', 'orange', 'TLE', 'warning'),
    'memory_limit_exceeded': JudgeStatusInfo('Memory Limit Exceeded', 'orange', 'MLE', 'warning'),
    'disk_limit_exceeded': JudgeStatusInfo('Disk Limit Exceeded', 'purple', 'DLE', 'warning'),
    'memory_leak': JudgeStatusInfo('Memory Leak', 'purple', 'Leak', 'warning'),

    'wrong_answer': JudgeStatusInfo('Wrong Answer', 'red', 'WA', 'danger'),
    'skipped': JudgeStatusInfo('Skipped', 'black', 'Skip', 'secondary'),
    'system_error': JudgeStatusInfo('System Error', 'gray-dark', 'SE', 'default'),
    'unknown_error': JudgeStatusInfo('Unknown Error', 'gray-dark', 'UKE', 'default'),

    'accepted': JudgeStatusInfo('Accepted', 'green', 'AC', 'success'),
}

language_info = {
    'cpp': 'C++',
    'git': 'Git',
    'verilog': 'Verilog',
}
