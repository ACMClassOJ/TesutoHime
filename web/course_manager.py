__all__ = ('CourseManager',)

from typing import Optional, Sequence, Set, Tuple

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
    def is_current(course: Course) -> bool:
        return course.term is None or g.time <= course.term.end_time
    @classmethod
    def can_join(cls, course: Course) -> bool:
        return cls.is_current(course)

    @staticmethod
    def can_read(course: Course) -> bool:
        return UserManager.get_course_privilege(g.user, course) >= PrivilegeType.readonly

    @staticmethod
    def can_write(course: Course) -> bool:
        return UserManager.get_course_privilege(g.user, course) >= PrivilegeType.owner


    @staticmethod
    def is_enrolled(user: User, course: Course) -> Tuple[bool, bool]:
        '''
        returns (is enrolled, is self-enrolled (i.e. observer))
        '''
        enrollment = UserManager.get_enrollment(user, course)
        if enrollment is None: return (False, False)
        return (True, enrollment.realname_reference is None)

    @classmethod
    def get_enrolled_courses(cls, user: User) -> Sequence[Course]:
        return [rr.course for rr in cls.get_enrolled_realname_references(user)]

    @staticmethod
    def get_enrolled_realname_references(user: User) -> Sequence[RealnameReference]:
        return [e.realname_reference for e in user.enrollments if e.realname_reference is not None]

    @classmethod
    def get_invited_courses(cls, user: User) -> Set[Course]:
        courses = set()
        course_ids = set(x.course_id for x in user.enrollments)
        for rr in user.realname_references:
            if rr.course_id not in course_ids:
                course = rr.course
                if not cls.can_join(course):
                    continue
                courses.add(course)
        return courses

    @classmethod
    def get_admin_courses(cls, user: User, current_only: bool = True) -> Sequence[Course]:
        courses = []
        for e in user.enrollments:
            if not e.admin: continue
            c = e.course
            if current_only and not cls.is_current(c): continue
            courses.append(c)
        courses.sort(key=lambda c: c.id, reverse=True)
        return courses

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
