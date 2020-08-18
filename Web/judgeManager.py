import sys
from utils import *

class JudgeManager:
    '''
    * ID: INT, auto_increment, PRIMARY KEY
    * Code: TEXT
    * User: TINYTEXT
    * Problem_ID: INT
    * Status: INT
    * Score: INT
    * Time: BIGINT // unix nano
    * Detail: MEDIUMTEXT // may exceed 64 KB
    '''
    def Add_Judge(self, Code: str, User: str, Problem_ID: int, Time: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Judge(Code, User, Problem_ID, Time, Status) VALUES('%s', '%s', '%s', '%s', '0')" % \
                           (Code, User, str(Problem_ID), str(Time)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Add_Judge\n")
        db.close()
        return

    def Update_Status(self, ID: int, NewStatus: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Judge SET Status = '%s' WHERE ID = '%s'" % (str(NewStatus), str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Update_Status\n")
        db.close()
        return

    def Update_After_Judge(self, ID: int, NewStatus: int, Score: int, Detail: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Judge SET Status = '%s', Score = '%s', Detail = '%s', WHERE ID = '%s'" % (str(NewStatus), str(ID), str(Score), Detail))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Update_After_Judge\n")
        db.close()
        return

    def Query_Judge(self, ID: int)->dict:
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, User, Problem_ID, Detail, Time FROM Judge WHERE ID = '%s'" % (str(ID)))
        data = cursor.fetchone()
        db.close()
        if data == None:
            return {}
        ret = {}
        ret['ID'] = int(data[0])
        ret['User'] = str(data[1])
        ret['Time'] = int(data[3])
        ret['Detail'] = str(data[2])
        return ret

    def Judge_In_Range(self, startID: int, endID: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, User, Problem_ID, Detail, Time FROM Judge WHERE ID >= '%s' and ID <= '%s'" % (str(startID), str(endID)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def Erase_Judge(self, ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Judge WHERE  ID = '%s'" % (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Erase_Judge\n")
        return
