__all__ = ('DiscussManager',)

from typing import Optional

from commons.models import Discussion, User
from web.utils import db


class DiscussManager:
    @staticmethod
    def add_discuss(problem_id: int, user: User, data: str):
        discuss = Discussion(problem_id=problem_id,
                             user_id=user.id,
                             data=data)
        db.add(discuss)

    @staticmethod
    def get_discussion(discussion_id: int) -> Optional[Discussion]:
        return db.get(Discussion, discussion_id)

    @staticmethod
    def delete_discuss(discussion: Discussion):
        db.delete(discussion)
