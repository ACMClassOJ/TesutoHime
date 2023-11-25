__all__ = ('UserManager',)

import hashlib
import random
import sys
from typing import Optional

from commons.models import ContestPlayer

from web.utils import SqlSession
from sqlalchemy import select, func, delete, update
from commons.models import User

def hash(password, salt):
    return str(hashlib.sha512((password + str(salt)).encode('utf-8')).hexdigest())


def rand_int():
    return random.randint(3456, 89786576)


class UserManager:
    @staticmethod
    def add_user(username: str, student_id: int, friendly_name: str, password: str,
                 privilege: int):  # will not check whether the argument is illegal
        salt = rand_int()
        password = hash(password, salt)
        user = User(username=username, student_id=student_id, friendly_name=friendly_name,
                    password=password, salt=salt, privilege=privilege)
        try:
            with SqlSession.begin() as db:
                db.add(user)
        except:
            sys.stderr.write("SQL Error in UserManager: addUser\n")
        return

    @staticmethod
    def modify_user(username: str, student_id: Optional[int], friendly_name: Optional[str],
                    password: Optional[str], privilege: Optional[int]):
        stmt = update(User).where(User.username == username)
        if student_id is not None:
            stmt = stmt.values(student_id=student_id)
        if friendly_name is not None:
            stmt = stmt.values(friendly_name=friendly_name)
        if password is not None:
            salt = rand_int()
            password = hash(password, salt)
            stmt = stmt.values(password=password, salt=salt)
        if privilege is not None:
            stmt = stmt.values(privilege=privilege)
        try:
            with SqlSession.begin() as db:
                db.execute(stmt)
        except:
            sys.stderr.write("SQL Error in UserManager: ModifyUser\n")

    @staticmethod
    def check_login(username: str, password: str) -> bool:
        with SqlSession() as db:
            stmt = select(User.password, User.salt).where(
                User.username == username)
            data = db.execute(stmt).first()
            if data is None:  # user do not exist
                return False
            h = hash(password, int(data[1]))
            return h == data[0]

    @staticmethod
    def get_friendly_name(username: str) -> str:  # Username must exist.
        with SqlSession() as db:
            stmt = select(User.friendly_name).where(User.username == username)
            return db.scalar(stmt)

    @staticmethod
    def get_canonical_username(username: str) -> str:  # Username must exist.
        """
        This function seems to be useless but in fact not. The login is NOT
        case sensitive (in mysql), while many other functions IS case
        sensitive, so we need the correct name.
        """
        with SqlSession() as db:
            stmt = select(User.username).where(User.username == username)
            return db.scalar(stmt)

    @staticmethod
    def get_student_id(username: str) -> Optional[str]:  # Username must exist.
        with SqlSession() as db:
            stmt = select(User.student_id).where(User.username == username)
            return db.scalar(stmt)

    @staticmethod
    def get_privilege(username: str) -> int:  # Username must exist.
        with SqlSession() as db:
            stmt = select(User.privilege).where(User.username == username)
            return db.scalar(stmt)

    @staticmethod
    def delete_user(username: str):
        with SqlSession.begin() as db:
            stmt = delete(User).where(User.username == username)
            db.execute(stmt)

    @staticmethod
    def has_user(username: str) -> bool:
        with SqlSession() as db:
            stmt = select(func.count()).where(User.username == username)
            return db.scalar(stmt) == 1

    @staticmethod
    def list_contests(username: str) -> bool:
        with SqlSession() as db:
            stmt = select(ContestPlayer.c.Belong) \
                .where(ContestPlayer.c.Username == username)
            return db.scalars(stmt).all()
