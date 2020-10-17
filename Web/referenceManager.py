import sys
from utils import *

class ReferenceManager:
    """
    Realname_Reference
    * ID: INT, auto_increment, PRIMARY KEY
    * Student_ID: TINYTEXT
    * Real_Name: TINYTEXT
    """
    def Add_Student(self, Student_ID, Real_Name):
        db = DB_Connect()
        cur = db.cursor()
        try:
            cur.execute("INSERT INTO Realname_Reference(Student_ID, Real_Name) VALUES(%s, %s)", (Student_ID, Real_Name))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ReferenceManager: Add_Student\n")
        db.close()

    def Query_Realname(self, Student_ID):
        db = DB_Connect()
        cur = db.cursor()
        cur.execute("SELECT Real_Name FROM Realname_Reference WHERE Student_ID = %s", (Student_ID, ))
        ret = cur.fetchone()
        if ret == None:
            return 'Unknown'
        return str(ret)

Reference_Manager = ReferenceManager()