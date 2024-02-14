from datetime import datetime
from math import ceil
from typing import List

from sqlalchemy import select

from commons.models import *
from scripts.db.env import Session

db = Session()

q = db.query(JudgeRecordV1) \
    .where(~select(JudgeRecordV2.id).where(JudgeRecordV2.id == JudgeRecordV1.id).exists()) \
    .order_by(JudgeRecordV1.id.asc())
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


for i in range(pages):
    page: List[JudgeRecordV1] = q.limit(page_size).offset(i * page_size).all()
    recs = []
    for s in page:
        rec = JudgeRecordV2(
            id=s.id,
            public=s.public,
            language=lang(s.language),
            created_at=time(s.time),
            user_id=s.user_id,
            problem_id=s.problem_id,
            status=stat(s.status),
            score=s.score,
            time_msecs=s.time_msecs,
            memory_bytes=s.memory_kbytes * 1024,
        )
        recs.append(rec)
    db.add_all(recs)
    db.flush()

input('Press enter to continue...')
db.commit()
