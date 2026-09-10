__all__ = ('DiscussManager',)

from typing import Optional

from commons.models import Discussion, Problem, User
from web.utils import db


class DiscussManager:
    @staticmethod
    def add_discuss(problem: Problem, user: User, data: str):
        discuss = Discussion(problem_id=problem.id,
                             user_id=user.id,
                             data=data)
        db.add(discuss)

    @staticmethod
    def get_discussion(problem: Problem, discussion_id: int) -> Optional[Discussion]:
        record = db.get(Discussion, discussion_id)
        if record is None: return record
        if record.problem_id != problem.id: return None
        return record

    @staticmethod
    def delete_discuss(discussion: Discussion):
        db.delete(discussion)
