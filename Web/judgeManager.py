from http.client import NOT_FOUND
from urllib.parse import urljoin

import requests
from config import S3Config, SchedulerConfig
from oldJudgeManager import Judge_Manager as old_judge_manager
from utils import SqlSession

from commons.models import JudgeRecord2, JudgeStatus


def key_from_submission_id(submission_id) -> str:
    return f'{submission_id}.code'

def schedule_judge(problem_id, submission_id, language, username):
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


def problem_judge_foreach(callback, problem_id):
    with SqlSession() as db:
        old_judger_max_id = old_judge_manager.max_id()
        submissions = db.query(JudgeRecord2.id).where(JudgeRecord2.problem_id == problem_id).all()
        for submission in submissions:
            if submission.id > old_judger_max_id:
                callback(submission.id)

class NotFoundException(Exception): pass
def mark_void(id):
    with SqlSession() as db:
        submission: JudgeRecord2 = db.query(JudgeRecord2).where(JudgeRecord2.id == id).one_or_none()
        if submission is None:
            raise NotFoundException()
        submission.details = None
        submission.status = JudgeStatus.void
        submission.message = 'Your judge result has been marked as void by an admin.'
        submission.score = 0
        db.commit()

def rejudge(id):
    with SqlSession() as db:
        submission: JudgeRecord2 = db.query(JudgeRecord2).where(JudgeRecord2.id == id).one_or_none()
        if submission is None:
            raise NotFoundException()
        # to avoid blocking judge queue too much,
        # use '_rejudge' as rate limit group
        schedule_judge(
            submission.problem_id,
            id,
            submission.language,
            '_rejudge',
        )

def abort_judge(id):
    url = urljoin(SchedulerConfig.base_url, f'submission/{id}/abort')
    res = requests.post(url)
    if res.status_code == NOT_FOUND:
        return
    if res.json()['result'] != 'ok':
        raise Exception('Runner error')
