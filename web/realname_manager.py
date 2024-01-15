__all__ = ('RealnameManager',)

import sys

from commons.models import RealnameReference
from web.utils import SqlSession
from sqlalchemy import select


class RealnameManager:
    @staticmethod
    def add_student(student_id, real_name):
        try:
            rr = RealnameReference(student_id=student_id, real_name=real_name)
            with SqlSession.begin() as db:
                db.add(rr)
        except Exception:
            sys.stderr.write("SQL Error in ReferenceManager: Add_Student\n")

    @staticmethod
    def query_realname(student_id):
        stmt = select(RealnameReference.real_name).where(RealnameReference.student_id == student_id) \
            .order_by(RealnameReference.id.desc()).limit(1)
        with SqlSession() as db:
            data = db.scalar(stmt)
            return data if data is not None and len(data) > 0 else 'Unknown'
