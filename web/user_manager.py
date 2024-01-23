__all__ = ('UserManager',)

import hashlib
from typing import Optional, Sequence

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import delete, func, select, update

from commons.models import ContestPlayer, User
from web.utils import db

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
    def check_login(username: str, password: str) -> bool:
        stmt = select(User.password).where(User.username == username)
        hashed = db.scalar(stmt)
        if hashed is None:  # user do not exist
            return False
        if hashed.startswith('$SHA512$'):
            raise Exception('Incomplete database migration!')
        if hashed.startswith(sha512_transition_prefix):
            result = verify_sha512(hashed, password)
            if not result:
                return False
            stmt1 = update(User).where(User.username == username) \
                .values(password=hash(password))
            db.execute(stmt1)
            return True
        return verify_argon2(hashed, password)

    @staticmethod
    def get_friendly_name(username: str) -> Optional[str]:
        stmt = select(User.friendly_name).where(User.username == username)
        return db.scalar(stmt)

    @staticmethod
    def get_canonical_username(username: str) -> Optional[str]:
        stmt = select(User.username).where(User.username_lower == func.lower(username))
        return db.scalar(stmt)

    @staticmethod
    def get_student_id(username: str) -> Optional[str]:
        stmt = select(User.student_id).where(User.username == username)
        return db.scalar(stmt)

    @staticmethod
    def get_privilege(username: str) -> Optional[int]:
        stmt = select(User.privilege).where(User.username == username)
        return db.scalar(stmt)

    @staticmethod
    def delete_user(username: str):
        stmt = delete(User).where(User.username == username)
        db.execute(stmt)

    @staticmethod
    def has_user(username: str) -> bool:
        stmt = select(func.count()).where(User.username == username)
        return db.scalar(stmt) == 1

    @staticmethod
    def list_contest_ids(username: str) -> Sequence[int]:
        stmt = select(ContestPlayer.c.contest_id) \
            .where(ContestPlayer.c.username == username)
        return db.scalars(stmt).all()
