from http.client import NOT_FOUND
from typing import List, Optional
from urllib.parse import urljoin

import requests
from flask import abort, g
from sqlalchemy.orm import defer, selectinload
from typing_extensions import TypeGuard

from commons.models import JudgeRecordV2, JudgeRunnerV2, JudgeStatus, User
from web.config import S3Config, SchedulerConfig
from web.contest_manager import ContestManager
from web.old_judge_manager import OldJudgeManager
from web.problem_manager import ProblemManager
from web.user_manager import UserManager
from web.utils import db, s3_internal


class NotFoundException(Exception): pass

class JudgeManager:
    @staticmethod
    def key_from_submission_id(submission_id) -> str:
        return f'{submission_id}.code'


    @staticmethod
    def schedule_judge(problem_id: int, submission_id: int, language: str, rate_limit_group: str):
        task = {
            'problem_id': str(problem_id),
            'submission_id': str(submission_id),
            'language': language,
            'source': {
                'bucket': S3Config.Buckets.submissions,
                'key': JudgeManager.key_from_submission_id(submission_id),
            },
            'rate_limit_group': rate_limit_group,
        }
        url = urljoin(SchedulerConfig.base_url, 'judge')
        try:
            res = requests.post(url, json=task).json()
            if res['result'] != 'ok':
                raise Exception(f'Scheduler error: {res["error"]}')
        except Exception as e:
            rec = db.get(JudgeRecordV2, submission_id)
            if rec is not None:
                rec.status = JudgeStatus.system_error
                rec.message = str(e)
                rec.score = 0

    @staticmethod
    def can_show(submission: Optional[JudgeRecordV2]) -> TypeGuard[JudgeRecordV2]:
        if submission is None:
            return False

        if ProblemManager.can_read(submission.problem):
            return True
        if not ProblemManager.can_show(submission.problem):
            return False
        if UserManager.user_enrolled_in_some_course_that_i_manage(submission.user, g.user):
            return True

        # exam first
        exam_id, is_exam_started = ContestManager.get_unfinished_exam_info_for_player(g.user)

        if exam_id != -1 and is_exam_started:
            # if the user is in a running exam, he can only see his own problems in exam.
            return submission.user_id == g.user.id and ContestManager.check_problem_in_contest(exam_id, submission.problem_id)
        else:
            # otherwise, the user can see his own and shared problems
            return submission.user_id == g.user.id or submission.public

    @staticmethod
    def can_write(submission: JudgeRecordV2) -> bool:
        return ProblemManager.can_write(submission.problem)

    @classmethod
    def can_abort(cls, submission: JudgeRecordV2) -> bool:
        return submission.status in \
            (JudgeStatus.pending, JudgeStatus.compiling, JudgeStatus.judging) and \
            (submission.user_id == g.user.id or cls.can_write(submission))


    @staticmethod
    def problem_judge_foreach(callback, problem_id) -> None:
        old_judger_max_id = OldJudgeManager.max_id()
        submissions = db \
            .query(JudgeRecordV2) \
            .where(JudgeRecordV2.problem_id == problem_id) \
            .all()
        for submission in submissions:
            if submission.id > old_judger_max_id:
                callback(submission)

    @staticmethod
    def mark_void(submission: JudgeRecordV2):
        submission.details = None
        submission.status = JudgeStatus.void
        submission.message = 'Your judge result has been marked as void by an admin.'
        submission.score = 0

    @staticmethod
    def rejudge(submission: JudgeRecordV2):
        # to avoid blocking judge queue too much,
        # use '_rejudge' as rate limit group
        JudgeManager.schedule_judge(
            submission.problem_id,
            submission.id,
            submission.language,
            '_rejudge',
        )

    @staticmethod
    def abort_judge(submission: JudgeRecordV2):
        url = urljoin(SchedulerConfig.base_url, f'submission/{submission.id}/abort')
        res = requests.post(url)
        if res.status_code == NOT_FOUND:
            return
        if res.json()['result'] != 'ok':
            raise Exception('Runner error')

    @staticmethod
    def create_submission(*, public: bool, language: str, user: User,
                          problem_id: int, code: str) -> JudgeRecordV2:
        rec = JudgeRecordV2(
            public=public,
            language=language,
            user_id=user.id,
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
                                    str(user.id))
        return rec

    @staticmethod
    def set_status(submission_id, status: str):
        rec = db.get(JudgeRecordV2, submission_id)
        if rec is None:
            abort(NOT_FOUND)
        rec.status = getattr(JudgeStatus, status)
        rec.details = None
        rec.message = None
        db.flush()

    @staticmethod
    def set_result(submission_id, *, score, status, message, details: str, time_msecs, memory_bytes):
        rec = db.get(JudgeRecordV2, submission_id)
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
        return db.get(JudgeRecordV2, submission_id)

    @staticmethod
    def list_runners() -> List[JudgeRunnerV2]:
        return db \
            .query(JudgeRunnerV2) \
            .where(JudgeRunnerV2.visible) \
            .order_by(JudgeRunnerV2.id) \
            .all()
