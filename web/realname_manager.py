__all__ = ('RealnameManager',)

import sys

from commons.models import RealnameReference
from web.utils import SqlSession
from sqlalchemy import select


class RealnameManager:
    """
    Realname_Reference
    * ID: INT, auto_increment, PRIMARY KEY
    * Student_ID: TINYTEXT
    * Real_Name: TINYTEXT
    """
    @staticmethod
    def Add_Student(Student_ID, Real_Name):
        try:
            rr = RealnameReference(student_id=Student_ID, real_name=Real_Name)
            with SqlSession.begin() as db:
                db.add(rr)
        except:
            sys.stderr.write("SQL Error in ReferenceManager: Add_Student\n")

    @staticmethod
    def Query_Realname(Student_ID):
        stmt = select(RealnameReference.real_name).where(RealnameReference.student_id == Student_ID) \
            .order_by(RealnameReference.id.desc()).limit(1)
        with SqlSession() as db:
            data = db.scalar(stmt)
            return data if data is not None and len(data) > 0 else 'Unknown'
