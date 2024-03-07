__all__ = ('RealnameManager',)

from typing import List, Optional, Sequence

from flask import g
from sqlalchemy import select

from commons.models import Contest, Course, Group, RealnameReference, User
from web.user_manager import UserManager
from web.utils import db


class RealnameManager:
    @classmethod
    def add_student(cls, student_id: str, real_name: str, course: Course, groups: List[Group]):
        rr = cls.query_realname_for_course(student_id, course.id)
        if rr is not None:
            db.delete(rr)
            db.flush()
        if real_name == 'delete':
            return
        rr = RealnameReference(student_id=student_id, real_name=real_name,
                               course_id=course.id)
        db.add(rr)
        db.flush()
        for group in groups:
            rr.groups.add(group)

    @staticmethod
    def query_realname_for_logs(student_id: str) -> str:
        stmt = select(RealnameReference.real_name) \
            .where(RealnameReference.student_id == student_id) \
            .order_by(RealnameReference.id.desc()).limit(1)
        data = db.scalar(stmt)
        return data if data is not None and len(data) > 0 else 'Unknown'

    @staticmethod
    def query_realname_for_course(student_id: str, course_id: int) -> Optional[RealnameReference]:
        stmt = select(RealnameReference) \
            .where(RealnameReference.student_id == student_id) \
            .where(RealnameReference.course_id == course_id)
        return db.scalar(stmt)

    @staticmethod
    def _can_read_criteria(user: User):
        if UserManager.has_site_owner_tag(user):
            return True
        rcids = UserManager.get_readable_course_ids(user)
        return RealnameReference.course_id.in_(rcids)

    @classmethod
    def query_realname_for_contest(cls, student_id: str, contest: Contest) -> Optional[RealnameReference]:
        from web.contest_manager import ContestManager
        if not ContestManager.can_read(contest):
            return None
        stmt = select(RealnameReference) \
            .where(RealnameReference.course_id == contest.course_id) \
            .where(RealnameReference.student_id == student_id)
        return db.scalar(stmt)

    @classmethod
    def query_realname_for_current_user(cls, student_id: str) -> Sequence[RealnameReference]:
        stmt = select(RealnameReference) \
            .where(RealnameReference.student_id == student_id) \
            .where(cls._can_read_criteria(g.user)) \
            .order_by(RealnameReference.id.desc())
        return [x for x in db.scalars(stmt)]
