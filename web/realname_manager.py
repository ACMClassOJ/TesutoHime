__all__ = ('RealnameManager',)

from commons.models import RealnameReference
from web.utils import db
from sqlalchemy import select


class RealnameManager:
    @staticmethod
    def add_student(student_id, real_name):
        rr = RealnameReference(student_id=student_id, real_name=real_name)
        db.add(rr)

    @staticmethod
    def query_realname(student_id):
        stmt = select(RealnameReference.real_name).where(RealnameReference.student_id == student_id) \
            .order_by(RealnameReference.id.desc()).limit(1)
        data = db.scalar(stmt)
        return data if data is not None and len(data) > 0 else 'Unknown'
