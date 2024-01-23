__all__ = ('DiscussManager',)

from typing import Optional, Sequence
from commons.models import Discussion
from web.utils import db
from sqlalchemy import update, select, delete

class DiscussManager:
    @staticmethod
    def add_discuss(problem_id: int, username: str, data: str):
        discuss = Discussion(problem_id=problem_id,
                             username=username,
                             data=data)
        db.add(discuss)

    @staticmethod
    def modify_discuss(discuss_id: int, new_data: str):
        stmt = update(Discussion) \
            .where(Discussion.id == discuss_id) \
            .values(data=new_data)
        db.execute(stmt)

    @staticmethod
    def get_author(discuss_id: int) -> Optional[str]:
        stmt = select(Discussion.username).where(Discussion.id == discuss_id)
        return db.scalar(stmt)

    @staticmethod
    def get_discuss_for_problem(problem_id: int) -> Sequence[Discussion]:
        stmt = select(Discussion).where(Discussion.problem_id == problem_id)
        return db.scalars(stmt).all()

    @staticmethod
    def delete_discuss(discuss_id: int):
        db.execute(delete(Discussion).where(Discussion.id == discuss_id))
