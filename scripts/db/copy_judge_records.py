from datetime import datetime
from math import ceil
from typing import List

from commons.models import *
from scripts.db.env import DATABASE_VERSION, Session


db = Session()
if db.query(DatabaseVersion).one().version != DATABASE_VERSION:
    raise Exception('Database version mismatch')

q = db.query(JudgeRecord)
count = q.count()
page_size = 10000
pages = ceil(count / page_size)

def lang(x: int) -> str:
    return ['cpp', 'git', 'verilog', 'quiz'][x]

def time(x: int) -> datetime:
    return datetime.fromtimestamp(float(x))

def stat(x: int) -> JudgeStatus:
    return [
        JudgeStatus.pending,
        JudgeStatus.judging,
        JudgeStatus.accepted,
        JudgeStatus.wrong_answer,
        JudgeStatus.compile_error,
        JudgeStatus.runtime_error,
        JudgeStatus.time_limit_exceeded,
        JudgeStatus.memory_limit_exceeded,
        JudgeStatus.memory_leak,
        JudgeStatus.system_error,
        JudgeStatus.disk_limit_exceeded,
    ][x]


checked_usernames = set()
bad_usernames = set()

checked_problems = set()
bad_problems = set()

for i in range(pages):
    page: List[JudgeRecord] = q.limit(page_size).offset(i * page_size).all()
    recs = []
    for s in page:
        if s.username not in checked_usernames:
            checked_usernames.add(s.username)
            u = db.query(User.id).where(User.username == s.username).one_or_none()
            if u == None:
                bad_usernames.add(s.username)
        if s.username in bad_usernames:
            print(f'Nonexistent user {s.username} at {s.id}')
            continue

        if s.problem_id not in checked_problems:
            checked_problems.add(s.problem_id)
            p = db.query(Problem.id).where(Problem.id == s.problem_id).one_or_none()
            if p == None:
                bad_problems.add(s.problem_id)
        if s.problem_id in bad_problems:
            print(f'Nonexistent problem {s.problem_id} at {s.id}')
            continue

        rec = JudgeRecord2(
            id=s.id,
            public=s.public,
            language=lang(s.language),
            created=time(s.time),
            username=s.username,
            problem_id=s.problem_id,
            status=stat(s.status),
            score=s.score,
            time_msecs=s.time_msecs,
            memory_bytes=s.memory_kbytes * 1024,
        )
        recs.append(rec)
    db.add_all(recs)

db.commit()
