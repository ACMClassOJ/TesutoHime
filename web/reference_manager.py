__all__ = ('ReferenceManager',)

import sys

from web.utils import db_connect


class ReferenceManager:
    """
    Realname_Reference
    * ID: INT, auto_increment, PRIMARY KEY
    * Student_ID: TINYTEXT
    * Real_Name: TINYTEXT
    """
    @staticmethod
    def Add_Student(Student_ID, Real_Name):
        db = db_connect()
        cur = db.cursor()
        try:
            cur.execute("INSERT INTO Realname_Reference(Student_ID, Real_Name) VALUES(%s, %s)", (Student_ID, Real_Name))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ReferenceManager: Add_Student\n")
        db.close()

    @staticmethod
    def Query_Realname(Student_ID):
        db = db_connect()
        cur = db.cursor()
        cur.execute("SELECT Real_Name FROM Realname_Reference WHERE Student_ID = %s ORDER BY ID DESC", (Student_ID, ))
        ret = cur.fetchone()
        if ret == None or len(ret) == 0:
            return 'Unknown'
        return str(ret[0])
