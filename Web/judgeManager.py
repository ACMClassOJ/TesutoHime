import sys
from utils import *

class JudgeManager:
    '''
    * ID: INT, auto_increment, PRIMARY KEY
    * Code: TEXT
    * User: TINYTEXT
    * Problem_ID: INT
    * Language: INT
    * Status: INT
    * Score: INT
    * Time: BIGINT // unix nano
    * Time_Used: INT // ms
    * Mem_Used: INT // Byte
    * Detail: MEDIUMTEXT // may exceed 64 KB
    '''
    def Add_Judge(self, Code: str, User: str, Problem_ID: int, Language: int, Time: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Judge(Code, User, Problem_ID, Language, Time, Status) VALUES(%s, %s, %s, %s, %s, '0')",
                           (Code, User, str(Problem_ID), str(Language), str(Time)))
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
            cursor.execute("UPDATE Judge SET Status = %s WHERE ID = %s", (str(NewStatus), str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Update_Status\n")
        db.close()
        return

    def Update_After_Judge(self, ID: int, NewStatus: int, Score: int, Detail: str, Time_Used: str, Mem_Used: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Judge SET Status = %s, Score = %s, Detail = %s, Time_Used = %s, Mem_Used = %s WHERE ID = %s", (str(NewStatus), str(ID), str(Score), Detail, Time_Used, Mem_Used))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Update_After_Judge\n")
        db.close()
        return

    def Query_Judge(self, ID: int)->dict: # for details
        db = DB_Connect()
        cur = db.cursor()
        cur.execute("SELECT ID, User, Problem_ID, Detail, Time, Time_Used, Mem_Used, Share FROM Judge WHERE ID = %s", (str(ID)))
        data = cursor.fetchone()
        db.close()
        if data == None:
            return {}
        ret = {}
        ret['ID'] = int(data[0])
        ret['User'] = str(data[1])
        ret['Problem_ID'] = int(data[2])
        ret['Detail'] = str(data[3])
        ret['Time'] = int(data[4])
        ret['Time_Used'] = int(data[5])
        ret['Mem_Used'] = int(data[6])
        ret['Share'] = bool(data[7])
        return ret

    def Max_ID(self):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Judge")
        data = cursor.fetchone()
        db.close()
        return int(data[0])

    def Judge_In_Range(self, startID: int, endID: int): # [{}], for page display.
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, User, Problem_ID, Time, Time_Used, Mem_Used, Status, Language, Share FROM Judge WHERE ID >= %s and ID <= %s ORDER BY ID desc", (str(startID), str(endID)))
        data = cursor.fetchall()
        ret = []
        for d in data:
            cur = {}
            cur['ID'] = int(d[0])
            cur['Username'] = str(d[1])
            cur['Problem_ID'] = int(d[2])
            cur['Time'] = int(d[3])
            cur['Time_Used'] = int(d[4])
            cur['Mem_Used'] = int(d[5])
            cur['Status'] = str(d[6])
            cur['Lang'] = str(d[7])
            cur['Share'] = bool(d[8])
            ret.append(cur)
        db.close()
        return ret

    def Get_Contest_Judge(self, Problem_ID: int, Username: str, Start_Time: int, End_Time: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Status, Score, Time FROM Judge WHERE Problem_ID = %s AND User = %s AND Time >= %s AND Time <= %s", (str(Problem_ID), Username, str(Start_Time), str(End_Time)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def Search_Judge(self, Arg_Submitter, Arg_Problem_ID, Arg_Status, Arg_Lang, Arg_Param = None):
        db = DB_Connect()
        cursor = db.cursor()
        com = 'SELECT ID, User, Problem_ID, Time, Time_Used, Mem_Used, Status, Language, Share FROM Judge WHERE '
        pre = []

        if Arg_Problem_ID != None:
            com = com + 'Problem_ID = %s'
            pre.append(str(Arg_Problem_ID))
        if Arg_Submitter != None:
            if len(pre):
                com = com + ' AND '
            com = com + 'User = %s'
            pre.append(str(Arg_Submitter))
        if Arg_Status != None:
            if len(pre):
                com = com + ' AND '
            com = com + 'Status = %s'
            pre.append(str(Arg_Status))
        if Arg_Lang != None:
            if len(pre):
                com = com + ' AND '
            com = com + 'Language = %s'
            pre.append(str(Arg_Lang))
        if Arg_Param == None:
            com = com + ' ORDER BY ID desc'
        else:
            com = com + ' ORDER BY Time_Used asc'
        cursor.execute(com, tuple(pre))
        ret = cursor.fetchall()
        db.close
        return ret

    def Search_AC(self, Problem_ID):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, User, Time_Used, Mem_Used, Language, Time FROM Judge WHERE Problem_ID = %s and Status = 2", (str(Problem_ID)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def Delete_Judge(self, ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Judge WHERE  ID = %s", (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Erase_Judge\n")
        return

Judge_Manager = JudgeManager()