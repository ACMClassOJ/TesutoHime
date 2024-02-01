__all__ = ('CourseManager',)

from typing import Optional, Sequence

from flask import g
from sqlalchemy import select

from commons.models import Course, Group, RealnameReference, User
from web.const import PrivilegeType
from web.user_manager import UserManager
from web.utils import db


class CourseManager:
    @staticmethod
    def get_course(course_id: int) -> Optional[Course]:
        return db.get(Course, course_id)

    @staticmethod
    def can_join(course: Course) -> bool:
        return course.term is None or g.time <= course.term.end_time

    @staticmethod
    def can_read(course: Course) -> bool:
        return UserManager.get_course_privilege(g.user, course) >= PrivilegeType.readonly

    @staticmethod
    def can_write(course: Course) -> bool:
        return UserManager.get_course_privilege(g.user, course) >= PrivilegeType.owner


    @classmethod
    def get_enrolled_courses(cls, user: User) -> Sequence[Course]:
        return [rr.course for rr in cls.get_enrolled_realname_references(user)]

    @staticmethod
    def get_enrolled_realname_references(user: User) -> Sequence[RealnameReference]:
        return [e.realname_reference for e in user.enrollments if e.realname_reference is not None]


    @staticmethod
    def get_group(group_id: int) -> Optional[Group]:
        return db.get(Group, group_id)

    @classmethod
    def get_group_in_course(cls, course: Course, group_id: int) -> Optional[Group]:
        group = cls.get_group(group_id)
        if group is None or group.course_id != course.id:
            return None
        return group

    @staticmethod
    def get_group_by_name(course: Course, group_name: str) -> Optional[Group]:
        stmt = select(Group) \
            .where(Group.course_id == course.id) \
            .where(Group.name == group_name)
        return db.scalar(stmt)
