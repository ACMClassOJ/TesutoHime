__all__ = ('UserManager',)

import hashlib
from typing import Optional, Sequence

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from flask import g
from sqlalchemy import func, select, update

from commons.models import (Contest, ContestPlayer, Course, Enrollment,
                            Problem, ProblemPrivilege, User)
from web.config import RedisConfig
from web.const import PrivilegeType
from web.utils import db, redis_connect

password_hasher = PasswordHasher()

def hash(password: str):
    return password_hasher.hash(password)

def hash_sha512(password, salt):
    return str(hashlib.sha512((password + str(salt)).encode('utf-8')).hexdigest())

def verify_argon2(hashed, password):
    try:
        return password_hasher.verify(hashed, password)
    except VerificationError:
        return False

sha512_transition_prefix = '$argon2+sha512$'

def verify_sha512(hashed, password):
    if not hashed.startswith(sha512_transition_prefix):
        return False
    hashed = hashed[len(sha512_transition_prefix):].split('$')
    salt = hashed[0]
    hashed = '$'.join(hashed[1:])
    return verify_argon2(hashed, hash_sha512(password, salt))


class UserManager:
    @staticmethod
    def add_user(username: str, student_id: str, friendly_name: str, password: str,
                 privilege: int):  # will not check whether the argument is illegal
        password = hash(password)
        user = User(username=username, student_id=student_id, friendly_name=friendly_name,
                    password=password, privilege=privilege)
        db.add(user)

    @staticmethod
    def modify_user(username: str, student_id: Optional[int], friendly_name: Optional[str],
                    password: Optional[str], privilege: Optional[int]):
        stmt = update(User).where(User.username == username)
        if student_id is not None:
            stmt = stmt.values(student_id=student_id)
        if friendly_name is not None:
            stmt = stmt.values(friendly_name=friendly_name)
        if password is not None:
            password = hash(password)
            stmt = stmt.values(password=password)
        if privilege is not None:
            stmt = stmt.values(privilege=privilege)
        db.execute(stmt)

    @staticmethod
    def check_login(user: User, password: str) -> bool:
        hashed = user.password
        if hashed is None:  # user do not exist
            return False
        if hashed.startswith('$SHA512$'):
            raise Exception('Incomplete database migration!')
        if hashed.startswith(sha512_transition_prefix):
            result = verify_sha512(hashed, password)
            if not result:
                return False
            user.password = hash(password)
            return True
        return verify_argon2(hashed, password)

    @staticmethod
    def get_user(user_id: int) -> Optional[User]:
        return db.get(User, user_id)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        return db.scalar(select(User).where(User.username_lower == func.lower(username)))

    @staticmethod
    def has_user(username: str) -> bool:
        return UserManager.get_user_by_username(username) is not None

    @staticmethod
    def list_contest_ids(user: User) -> Sequence[int]:
        stmt = select(ContestPlayer.contest_id) \
            .where(ContestPlayer.user_id == user.id)
        return db.scalars(stmt).all()

    redis = redis_connect()

    @staticmethod
    def _privileges_redis_key(user: User) -> str:
        return f'{RedisConfig.prefix}priv:{user.id}'

    @classmethod
    def _privileges_cache_get(cls, user: User, type: str, id: Optional[int] = None) -> Optional[str]:
        hash_key = f'{type}{":" + str(id) if id is not None else ""}'
        if 'privilege_cache' not in g:
            g.privilege_cache = {}
        if hash_key in g.privilege_cache:
            return g.privilege_cache[hash_key]
        redis_key = cls._privileges_redis_key(user)
        cached = cls.redis.hget(redis_key, hash_key)
        g.privilege_cache[hash_key] = cached
        return cached

    @classmethod
    def _privileges_cache_set(cls, user: User, type: str, id: Optional[int], content: str) -> None:
        hash_key = f'{type}{":" + str(id) if id is not None else ""}'
        redis_key = cls._privileges_redis_key(user)
        if 'privilege_cache' not in g:
            g.privilege_cache = {}
        g.privilege_cache[hash_key] = content
        cls.redis.hset(redis_key, hash_key, content)
        cls.redis.expire(redis_key, 3600)

    @staticmethod
    def get_enrollment(user: User, course: Course) -> Optional[Enrollment]:
        stmt = select(Enrollment) \
            .where(Enrollment.user_id == user.id) \
            .where(Enrollment.course_id == course.id)
        return db.scalar(stmt)

    @classmethod
    def has_site_owner_tag(cls, user: User) -> bool:
        cached = cls._privileges_cache_get(user, 'siteowner')
        if cached is not None:
            return cached == 't'

        has_site_owner_tag = False
        for c in user.courses:
            enrollment = cls.get_enrollment(user, c)
            assert enrollment is not None
            if enrollment.admin and c.tag is not None and c.tag.site_owner:
                has_site_owner_tag = True
                break

        cls._privileges_cache_set(user, 'siteowner', None, 't' if has_site_owner_tag else 'f')
        return has_site_owner_tag

    @classmethod
    def get_course_privilege(cls, user: User, course: Course) -> PrivilegeType:
        cached = cls._privileges_cache_get(user, 'course', course.id)
        if cached is not None:
            return getattr(PrivilegeType, cached)

        priv = PrivilegeType.no_privilege
        enrollment = cls.get_enrollment(user, course)
        if enrollment is not None and enrollment.admin:
            priv = PrivilegeType.owner
        elif cls.has_site_owner_tag(user):
            priv = PrivilegeType.owner
        else:
            for c in user.courses:
                if c.tag_id == course.tag_id:
                    enrollment = cls.get_enrollment(user, c)
                    if enrollment is not None and enrollment.admin:
                        priv = PrivilegeType.readonly
                        break

        cls._privileges_cache_set(user, 'course', course.id, priv.name)
        return priv

    @classmethod
    def get_contest_privilege(cls, user: User, contest: Contest) -> PrivilegeType:
        cached = cls._privileges_cache_get(user, 'contest', contest.id)
        if cached is not None:
            return getattr(PrivilegeType, cached)

        courses = set(g.course for g in contest.groups)
        priv = PrivilegeType.no_privilege
        for c in courses:
            priv = max(priv, cls.get_course_privilege(user, c))
            if priv == PrivilegeType.owner:
                break

        cls._privileges_cache_set(user, 'contest', contest.id, priv.name)
        return priv

    @classmethod
    def get_problem_privilege(cls, user: User, problem: Problem) -> PrivilegeType:
        cached = cls._privileges_cache_get(user, 'problem', problem.id)
        if cached is not None:
            return getattr(PrivilegeType, cached)

        priv = PrivilegeType.no_privilege
        if cls.has_site_owner_tag(user):
            priv = PrivilegeType.owner
        else:
            prob_priv = db.scalar(select(ProblemPrivilege) \
                .where(ProblemPrivilege.user_id == user.id) \
                .where(ProblemPrivilege.problem_id == problem.id))
            if prob_priv is not None:
                priv = getattr(PrivilegeType, prob_priv.privilege.name)
        if priv != PrivilegeType.owner:
            priv = max(priv, cls.get_course_privilege(user, problem.course))

        cls._privileges_cache_set(user, 'course', problem.id, priv.name)
        return priv

    @classmethod
    def get_readable_course_ids(cls, user: User) -> Sequence[int]:
        cached = cls._privileges_cache_get(user, 'rcid')
        if cached is not None:
            return [int(x) for x in cached.split(',') if x != '']

        tag_ids = set()
        for c in user.courses:
            enrollment = cls.get_enrollment(user, c)
            assert enrollment is not None
            if enrollment.admin:
                tag_ids.add(c.tag_id)
        stmt = select(Course.id).where(Course.tag_id.in_(tag_ids))
        course_ids = [x for x in db.scalars(stmt)]

        cls._privileges_cache_set(user, 'rcid', None, ','.join(str(x) for x in course_ids))
        return course_ids

    @classmethod
    def flush_privileges(cls, user: User):
        cls.redis.delete(cls._privileges_redis_key(user))
