from itertools import groupby
from os import makedirs
from typing import *

from boto3 import client as s3_client
from botocore.config import Config

from commons.task_typing import *
from commons.util import deserialize
from scheduler2.config import s3_connection
from scripts.db.env import *

cfg = Config(signature_version='s3v4')
s3 = s3_client('s3', **s3_connection, config=cfg)

db = Session()

def filename (s: JudgeRecordV2) -> str:
    return f'{s.user.student_id}-{names[s.user.username]}-{s.user.username}-{s.id}-T{s.problem.id}-{s.status.name}-{s.score}.cpp'

def prelude (s: JudgeRecordV2) -> str:
    details_message = 'No details'
    message = s.message
    if message is not None:
        message = '\n * '.join(message.split('\n'))
    if s.details is not None:
        details: ProblemJudgeResult = deserialize(s.details)
        details_message = '\n * '.join(f'{group.name}: {group.score} {group.result}' for group in details.groups)
    return f'''
/**
 * {s.user.student_id} {names[s.user.username]} ({s.user.username})
 * Problem {s.problem_id} - {s.problem.title}
 * Time: {s.created_at.strftime('%Y-%m-%d %H:%M:%S')}
 * Status: {s.status.name}
 * Score: {s.score}
 * Message: {message}
 *
 * {details_message}
 */
'''.strip() + '\n\n'

bucket = input('S3 bucket name (oj-submissions): ')
if bucket == '': bucket = 'oj-submissions'
contest_id = int(input('Contest ID: '))

def get_realname(user):
    rec = db \
        .query(RealnameReference.real_name) \
        .where(RealnameReference.student_id == user.student_id) \
        .all()
    if len(rec) == 0: return 'Unknown'
    return rec[-1][0]

contest = db.query(Contest).where(Contest.id == contest_id).one()
names = dict((x.username, get_realname(x)) for x in contest.players)
problems = db.query(ContestProblem.problem_id).where(ContestProblem.contest_id == contest_id).all()
submissions: List[JudgeRecordV2] = db \
    .query(JudgeRecordV2) \
    .where(JudgeRecordV2.problem_id.in_(x[0] for x in problems)) \
    .where(JudgeRecordV2.username.in_(x.username for x in contest.players)) \
    .where(JudgeRecordV2.created_at >= contest.start_time) \
    .where(JudgeRecordV2.created_at < contest.end_time) \
    .all()
submissions: List[JudgeRecordV2] = sorted(submissions, key=lambda x: (x.username, x.problem_id))

for _, tries in groupby(submissions, lambda x: (x.username, x.problem_id)):
    tries = list(tries)
    score = max(x.score for x in tries)
    score_tries = list(sorted(filter(lambda x: x.score == score, tries), key=lambda x: x.id))
    s = score_tries[-1]
    dir = f'export/{s.problem_id}'
    makedirs(dir, exist_ok=True)
    r = s3.get_object(Bucket=bucket, Key=f'{s.id}.code')['Body'].read().decode(errors='replace')
    with open(f'{dir}/{filename(s)}', 'w') as w:
        w.write(prelude(s))
        w.write(r)
