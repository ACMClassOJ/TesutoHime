from http.client import NOT_FOUND
from typing import List, Optional
from urllib.parse import urljoin

import requests
from flask import abort
from sqlalchemy.orm import defer, selectinload

from commons.models import JudgeRecordV2, JudgeRunnerV2, JudgeStatus
from web.config import S3Config, SchedulerConfig
from web.old_judge_manager import OldJudgeManager
from web.utils import db, s3_internal


class NotFoundException(Exception): pass

class JudgeManager:
    @staticmethod
    def key_from_submission_id(submission_id) -> str:
        return f'{submission_id}.code'


    @staticmethod
    def schedule_judge(problem_id, submission_id, language, username):
        task = {
            'problem_id': str(problem_id),
            'submission_id': str(submission_id),
            'language': language,
            'source': {
                'bucket': S3Config.Buckets.submissions,
                'key': JudgeManager.key_from_submission_id(submission_id),
            },
            'rate_limit_group': username,
        }
        url = urljoin(SchedulerConfig.base_url, 'judge')
        try:
            res = requests.post(url, json=task).json()
            if res['result'] != 'ok':
                raise Exception(f'Scheduler error: {res["error"]}')
        except Exception as e:
            rec: JudgeRecordV2 = db \
                .query(JudgeRecordV2) \
                .where(JudgeRecordV2.id == submission_id) \
                .one()
            rec.status = JudgeStatus.system_error
            rec.message = str(e)
            rec.score = 0


    @staticmethod
    def problem_judge_foreach(callback, problem_id):
        old_judger_max_id = OldJudgeManager.max_id()
        submissions = db \
            .query(JudgeRecordV2.id) \
            .where(JudgeRecordV2.problem_id == problem_id) \
            .all()
        for submission in submissions:
            if submission.id > old_judger_max_id:
                callback(submission.id)

    @staticmethod
    def mark_void(id):
        submission: JudgeRecordV2 = db \
            .query(JudgeRecordV2) \
            .where(JudgeRecordV2.id == id) \
            .one_or_none()
        if submission is None:
            raise NotFoundException()
        submission.details = None
        submission.status = JudgeStatus.void
        submission.message = 'Your judge result has been marked as void by an admin.'
        submission.score = 0

    @staticmethod
    def rejudge(id):
        submission: JudgeRecordV2 = db \
            .query(JudgeRecordV2) \
            .where(JudgeRecordV2.id == id) \
            .one_or_none()
        if submission is None:
            raise NotFoundException()
        # to avoid blocking judge queue too much,
        # use '_rejudge' as rate limit group
        JudgeManager.schedule_judge(
            submission.problem_id,
            id,
            submission.language,
            '_rejudge',
        )

    @staticmethod
    def abort_judge(id):
        url = urljoin(SchedulerConfig.base_url, f'submission/{id}/abort')
        res = requests.post(url)
        if res.status_code == NOT_FOUND:
            return
        if res.json()['result'] != 'ok':
            raise Exception('Runner error')

    @staticmethod
    def add_submission(*, public, language, username, problem_id, code) -> int:
        rec = JudgeRecordV2(
            public=public,
            language=language,
            username=username,
            problem_id=problem_id,
            status=JudgeStatus.pending,
        )
        db.add(rec)
        db.flush()
        submission_id = rec.id
        key = JudgeManager.key_from_submission_id(submission_id)
        bucket = S3Config.Buckets.submissions
        s3_internal.put_object(Bucket=bucket, Key=key, Body=code.encode())
        JudgeManager.schedule_judge(problem_id, submission_id, language,
                                    username)
        return submission_id

    @staticmethod
    def set_status(submission_id, status: str):
        rec: JudgeRecordV2 = db \
            .query(JudgeRecordV2) \
            .where(JudgeRecordV2.id == submission_id) \
            .one_or_none()
        if rec is None:
            abort(NOT_FOUND)
        rec.status = getattr(JudgeStatus, status)
        rec.details = None
        rec.message = None

    @staticmethod
    def set_result(submission_id, *, score, status, message, details: str, time_msecs, memory_bytes):
        rec: JudgeRecordV2 = db \
            .query(JudgeRecordV2) \
            .where(JudgeRecordV2.id == submission_id) \
            .one_or_none()
        if rec is None:
            abort(NOT_FOUND)
        rec.score = score
        rec.status = status
        rec.message = message
        rec.details = details
        rec.time_msecs = time_msecs
        rec.memory_bytes = memory_bytes
        db.flush()

    @staticmethod
    def list_accepted_submissions(problem_id: int) -> List[JudgeRecordV2]:
        return db \
            .query(JudgeRecordV2) \
            .options(defer(JudgeRecordV2.details), defer(JudgeRecordV2.message)) \
            .options(selectinload(JudgeRecordV2.user)) \
            .where(JudgeRecordV2.problem_id == problem_id) \
            .where(JudgeRecordV2.status == JudgeStatus.accepted) \
            .all()

    @staticmethod
    def get_submission(submission_id: int) -> Optional[JudgeRecordV2]:
        return db \
            .query(JudgeRecordV2) \
            .where(JudgeRecordV2.id == submission_id) \
            .one_or_none()

    @staticmethod
    def list_runners() -> List[JudgeRunnerV2]:
        return db \
            .query(JudgeRunnerV2) \
            .where(JudgeRunnerV2.visible) \
            .order_by(JudgeRunnerV2.id) \
            .all()
