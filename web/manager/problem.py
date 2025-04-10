from http.client import BAD_REQUEST
from typing import List, Optional
from unicodedata import normalize

import sqlalchemy as sa
from flask import abort, g
from sqlalchemy import func, select
from sqlalchemy.orm import load_only
from typing_extensions import TypeGuard

from commons.models import (ContestProblem, Course, JudgeRecordV2, Problem,
                            ProblemAttachment)
from web.config import S3Config
from web.const import FAR_FUTURE_TIME, MAX_ATTACHMENT_SIZE_BYTES, PrivilegeType, language_info
from web.manager.contest import ContestManager
from web.manager.user import UserManager
from web.utils import SearchDescriptor, db, generate_s3_public_url, s3_internal


class ProblemManager:
    @classmethod
    def create_problem(cls, course: Course) -> Problem:
        problem_id = cls.get_max_id() + 1
        problem = Problem(
            id=problem_id,
            title='新建题目',
            release_time=FAR_FUTURE_TIME,
            course_id=course.id,
        )
        db.add(problem)
        db.flush()
        return problem

    @staticmethod
    def hide_problem(problem: Problem):
        problem.release_time = FAR_FUTURE_TIME

    @staticmethod
    def show_problem(problem: Problem):
        problem.release_time = g.time

    @staticmethod
    def get_problem(problem_id: int) -> Optional[Problem]:
        return db.get(Problem, problem_id)

    @staticmethod
    def languages_accepted(problem: Problem) -> List[str]:
        if problem.languages_accepted is not None:
            return problem.languages_accepted
        default_languages = []
        for k in language_info:
            if language_info[k].acceptable_by_default:
                default_languages.append(k)
        return default_languages

    @staticmethod
    def get_max_id() -> int:
        stmt = select(func.max(Problem.id)).where(Problem.id < 11000)
        data = db.scalar(stmt)
        return data if data is not None else 0

    @staticmethod
    def can_show(problem: Optional[Problem]) -> TypeGuard[Problem]:
        return problem is not None and \
            (problem.release_time <= g.time or \
                UserManager.get_problem_privilege(g.user, problem) >= PrivilegeType.readonly)

    @staticmethod
    def can_read(problem: Problem) -> bool:
        return UserManager.get_problem_privilege(g.user, problem) >= PrivilegeType.readonly

    @staticmethod
    def can_write(problem: Problem) -> bool:
        return UserManager.get_problem_privilege(g.user, problem) >= PrivilegeType.owner

    @staticmethod
    def delete_problem(problem: Problem):
        submission_count = db.scalar(select(func.count())
                                     .where(JudgeRecordV2.problem_id == problem.id))
        contest_count = db.scalar(select(func.count())
                                  .where(ContestProblem.problem_id == problem.id))
        assert submission_count is not None
        assert contest_count is not None
        if submission_count > 0 or contest_count > 0 or len(problem.attachments) > 0:
            abort(BAD_REQUEST)
        db.delete(problem)


    # Attachments

    @staticmethod
    def normalize_and_validate_filename(filename: str) -> str:
        filename = normalize('NFKC', filename)

        if len(filename.encode()) > 512:
            raise ValueError('Filename too long')
        if '\x00' in filename or '/' in filename:
            raise ValueError('Filename contains forbidden character')
        if filename == '.' or filename == '..':
            raise ValueError('Filename is . or ..')

        return filename

    @staticmethod
    def attachment_quota_used_bytes(course: Course) -> int:
        query = select(func.sum(ProblemAttachment.size_bytes)).join(Problem).where(Problem.course_id == course.id)
        used = db.scalar(query)
        if used is None: return 0
        return used

    @classmethod
    def attachment_quota_remaining_bytes(cls, course: Course) -> int:
        remaining = course.attachment_quota_bytes - cls.attachment_quota_used_bytes(course)
        return max(0, remaining)

    @staticmethod
    def get_attachment(problem: Problem, name: str) -> Optional[ProblemAttachment]:
        return db.scalar(select(ProblemAttachment)
                         .where(ProblemAttachment.problem_id == problem.id)
                         .where(ProblemAttachment.name == name))

    @classmethod
    def create_attachment(cls, problem: Problem, filename: str, size_bytes: int) -> ProblemAttachment:
        if size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
            raise ValueError('Attachment too large. Please contact OJ maintainers to proceed.')
        if size_bytes < 0:
            raise ValueError('Invalid attachment size')

        filename = cls.normalize_and_validate_filename(filename)
        quota_remaining = cls.attachment_quota_remaining_bytes(problem.course)
        if cls.get_attachment(problem, filename):
            raise ValueError('Attachment with this name already exists')
        # In theory, there is a TOC/TOU problem.
        # In practice, we don't care about admins using their disk
        # space a bit more than allocated.
        if size_bytes > quota_remaining:
            raise ValueError('Attachment quota exceeded for this course. Please contact OJ maintainers to raise the quota.')

        attachment = ProblemAttachment(problem_id=problem.id, user_id=g.user.id,
                                       name=filename, size_bytes=size_bytes)
        db.add(attachment)
        db.flush()

        return attachment

    @classmethod
    def delete_attachment(cls, attachment: ProblemAttachment):
        s3_internal.delete_object(Bucket=S3Config.Buckets.attachments,
                                  Key=cls.key_of_attachment(attachment))
        db.delete(attachment)

    @staticmethod
    def key_of_attachment(attachment: ProblemAttachment) -> str:
        return f'{attachment.problem_id}/{attachment.name}'

    @classmethod
    def upload_url_of_attachment(cls, attachment: ProblemAttachment) -> str:
        return generate_s3_public_url('put_object', {
            'Bucket': S3Config.Buckets.attachments,
            'Key': cls.key_of_attachment(attachment),
            'ContentLength': attachment.size_bytes,
            'IfNoneMatch': '*',
        }, ExpiresIn=3600)

    @classmethod
    def download_url_of_attachment(cls, attachment: ProblemAttachment) -> str:
        return generate_s3_public_url('get_object', {
            'Bucket': S3Config.Buckets.attachments,
            'Key': cls.key_of_attachment(attachment),
        }, ExpiresIn=60)


    class ProblemSearch(SearchDescriptor):
        __model__ = Problem
        __order__ = 'asc'

        @staticmethod
        def __base_query__():
            query = select(Problem).options(load_only(Problem.id, Problem.title, Problem.problem_type))
            if not UserManager.has_site_owner_tag(g.user):
                readable_course_ids = UserManager.get_readable_course_ids(g.user)
                query = query.where(sa.or_(Problem.release_time <= g.time,
                                           Problem.course_id.in_(readable_course_ids)))
            return query

        @staticmethod
        def keyword(keyword: str):
            return sa.func.strpos(Problem.title, keyword) > 0

        @staticmethod
        def type(type: int):
            return Problem.problem_type == type

        @staticmethod
        def problemset_id(id: int):
            contest = ContestManager.get_contest(id)
            if contest is None: return False
            problem_ids = ContestManager.list_problem_for_contest(contest)
            return Problem.id.in_(problem_ids)
