__all__ = ('CourseManager',)

from typing import Optional

from flask import g
from sqlalchemy import select

from commons.models import Course, Group
from web.const import PrivilegeType
from web.user_manager import UserManager
from web.utils import db


class CourseManager:
    @staticmethod
    def get_course(course_id: int) -> Optional[Course]:
        return db.get(Course, course_id)

    @staticmethod
    def can_read(course: Course) -> bool:
        return UserManager.get_course_privilege(g.user, course) >= PrivilegeType.readonly

    @staticmethod
    def can_write(course: Course) -> bool:
        return UserManager.get_course_privilege(g.user, course) >= PrivilegeType.owner

    @staticmethod
    def get_group_by_name(course: Course, group_name: str) -> Optional[Group]:
        stmt = select(Group) \
            .where(Group.course_id == course.id) \
            .where(Group.name == group_name)
        return db.scalar(stmt)
