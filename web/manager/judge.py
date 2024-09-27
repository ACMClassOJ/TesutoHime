from http.client import NOT_FOUND, OK
from typing import List, Optional
from urllib.parse import quote, urljoin

import requests
from flask import abort, g
from sqlalchemy import select
from sqlalchemy.orm import defer, selectinload
from typing_extensions import TypeGuard

from commons.models import JudgeRecordV2, JudgeRunnerV2, JudgeStatus, Problem, User
from commons.util import deserialize
from web.config import ProblemConfig, S3Config, SchedulerConfig
from web.manager.contest import ContestManager
from web.manager.old_judge import OldJudgeManager
from web.manager.problem import ProblemManager
from web.manager.user import UserManager
from web.utils import SearchDescriptor, db, generate_s3_public_url, s3_internal


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
    def can_create(problem: Problem, public: bool, language: str, code: str) -> bool:
        if g.in_exam or not problem.allow_public_submissions:
            if public: return False
        if language not in ProblemManager.languages_accepted(problem):
            return False
        if len(code) > ProblemConfig.Max_Code_Length:
            return False
        return True


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
    def get_details(submission: JudgeRecordV2):
        details = deserialize(submission.details) if submission.details is not None else None
        if details is None and submission.status == JudgeStatus.judging:
            url = f'submission/{quote(str(submission.id))}/status'
            # TODO: caching
            res = requests.get(urljoin(SchedulerConfig.base_url, url))
            if res.status_code == OK:
                details = deserialize(res.text)
            elif res.status_code == NOT_FOUND:
                pass
            else:
                raise Exception(f'Unknown status code {res.status_code} fetching judge status')
        return details

    @staticmethod
    def sign_code_url(submission: JudgeRecordV2) -> str:
        return generate_s3_public_url('get_object', {
            'Bucket': S3Config.Buckets.submissions,
            'Key': JudgeManager.key_from_submission_id(submission.id),
        }, ExpiresIn=60)

    @classmethod
    def should_show_score(cls, submission: JudgeRecordV2) -> bool:
        return (
            not cls.can_abort(submission) and
            submission.status not in (JudgeStatus.void, JudgeStatus.aborted)
        )

    @staticmethod
    def list_runners() -> List[JudgeRunnerV2]:
        return db \
            .query(JudgeRunnerV2) \
            .where(JudgeRunnerV2.visible) \
            .order_by(JudgeRunnerV2.id) \
            .all()

    class SubmissionSearch(SearchDescriptor):
        __model__ = JudgeRecordV2

        @staticmethod
        def __base_query__():
            return select(JudgeRecordV2) \
                .options(defer(JudgeRecordV2.details), defer(JudgeRecordV2.message)) \
                .options(selectinload(JudgeRecordV2.user).load_only(User.student_id, User.friendly_name)) \
                .options(selectinload(JudgeRecordV2.problem).load_only(Problem.title))

        @staticmethod
        def username(username: str):
            user = UserManager.get_user_by_username(username)
            if user is None: return False
            return JudgeRecordV2.user_id == user.id

        @staticmethod
        def problem_id(id: int):
            return JudgeRecordV2.problem_id == id

        @staticmethod
        def status(status: str):
            s = getattr(JudgeStatus, status, None)
            if not isinstance(s, JudgeStatus):
                return False
            return JudgeRecordV2.status == s

        @staticmethod
        def lang(lang: str):
            return JudgeRecordV2.language == lang
