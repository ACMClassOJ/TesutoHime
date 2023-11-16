__all__ = ('DiscussManager',)

import sys

from typing import List
from commons.models import Discuss
from web.utils import SqlSession, unix_nano
from sqlalchemy import update, select, delete

class DiscussManager:
    @staticmethod
    def add_discuss(problem_id: int, username: str, data: str):
        discuss = Discuss(problem_id=problem_id,
                          username=username,
                          data=data,
                          time=unix_nano())
        try:
            with SqlSession.begin() as db:
                db.add(discuss)
        except:
            sys.stderr.write("SQL Error in DiscussManager: Add_Discuss\n")

    @staticmethod
    def modify_discuss(discuss_id: int, new_data: str):
        stmt = update(Discuss).where(Discuss.id == discuss_id) \
            .values(data=new_data)
        try:
            with SqlSession.begin() as db:
                db.execute(stmt)
        except:
            sys.stderr.write("SQL Error in DiscussManager: Modify_Discuss\n")

    @staticmethod
    def get_author(discuss_id: int) -> str:
        with SqlSession() as db:
            stmt = select(Discuss.username).where(Discuss.id == discuss_id)
            return db.scalar(stmt)

    @staticmethod
    def get_discuss_for_problem(problem_id: int) -> List[Discuss]:
        stmt = select(Discuss).where(Discuss.problem_id == problem_id)
        with SqlSession() as db:
            data = db.scalars(stmt).all()
            return data

    @staticmethod
    def delete_discuss(discuss_id: int):
        try:
            with SqlSession.begin() as db:
                stmt = delete(Discuss).where(Discuss.id == discuss_id)
                db.execute(stmt)
        except:
            sys.stderr.write("SQL Error in DiscussManager: Delete_Discuss\n")
