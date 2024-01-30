__all__ = ('RealnameManager',)

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import aliased

from commons.models import (ContestGroup, Course, Enrollment,
                            GroupRealnameReference, RealnameReference, User)
from web.user_manager import UserManager
from web.utils import db


class RealnameManager:
    @staticmethod
    def add_student(student_id, real_name):
        # TODO: course
        rr = RealnameReference(student_id=student_id, real_name=real_name)
        db.add(rr)

    @staticmethod
    def query_realname(student_id: str) -> str:
        stmt = select(RealnameReference.real_name) \
            .where(RealnameReference.student_id == student_id) \
            .order_by(RealnameReference.id.desc()).limit(1)
        data = db.scalar(stmt)
        return data if data is not None and len(data) > 0 else 'Unknown'

    @staticmethod
    def query_realname_for_course(student_id: str, course_id: int) -> Sequence[RealnameReference]:
        stmt = select(RealnameReference) \
            .where(RealnameReference.student_id == student_id) \
            .where(RealnameReference.course_id == course_id) \
            .order_by(RealnameReference.id.desc())
        return [x for x in db.scalars(stmt)]

    @staticmethod
    def _can_read_criteria(user: User):
        if UserManager.has_site_owner_tag(user):
            return True
        student_enrollment = aliased(Enrollment)
        user_enrollment = aliased(Enrollment)
        student_course = aliased(Course)
        user_course = aliased(Course)
        return select(student_enrollment.id) \
            .join(student_course) \
            .join(user_course, user_course.tag_id == student_course.tag_id) \
            .join(user_enrollment) \
            .where(RealnameReference.course_id == student_enrollment.course_id) \
            .where(user_enrollment.user_id == user.id) \
            .where(user_enrollment.admin) \
            .exists()

    @classmethod
    def query_realname_for_contest_user(cls, student_id: str, contest_id: int, user: User) -> Sequence[RealnameReference]:
        groups = db.scalars(select(ContestGroup.group_id).where(ContestGroup.contest_id == contest_id))
        stmt = select(RealnameReference) \
            .join(GroupRealnameReference) \
            .where(GroupRealnameReference.group_id.in_(groups)) \
            .where(RealnameReference.student_id == student_id) \
            .where(cls._can_read_criteria(user)) \
            .order_by(RealnameReference.id.desc())
        return [x for x in db.scalars(stmt)]

    @classmethod
    def query_realname_for_user(cls, student_id: str, user: User) -> Sequence[RealnameReference]:
        # TODO: measure DB perf
        stmt = select(RealnameReference) \
            .where(RealnameReference.student_id == student_id) \
            .where(cls._can_read_criteria(user)) \
            .order_by(RealnameReference.id.desc())
        return [x for x in db.scalars(stmt)]
