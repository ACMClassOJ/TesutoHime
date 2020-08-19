import sys
from utils import *

class DiscussManager:
    def Add_Discuss(self, Problem_ID: int, Username: str, Data: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Discuss(Problem_ID, Username, Data) VALUES(%s, %s, %s, 0)",
                           (str(Problem_ID), Username, Data))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Add_Discuss\n")
            db.close()
        return
    def Modify_Discuss(self, ID: int, NewData: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Discuss SET DATA = %s WHERE ID = %s", (NewData, str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Modify_Discuss\n")
            db.close()
        return

    def Get_Discuss_For_Problem(self, ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username, DATA FROM Discuss WHERE Problem_ID = %s", (str(ID)))
        ret = cursor.fetchall()
        return ret

    def Delete_Discuss(self, ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Discuss WHERE ID = %s", (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Erase_Discuss\n")
            db.close()
        return
