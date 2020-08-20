import sys
from utils import *

class ConetstManager:
    def Create_Contest(self, Name: str, Start_Time: int, End_Time: int, Type: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Contest (Name, Start_Time, End_Time, Type) VALUES (%s, %s, %s, %s)",
                           (Name, str(Start_Time), str(End_Time), str(Type)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Create_Contest\n")
        db.close()
        return

    def Modify_Contest(self, ID: int, New_Name: str, New_Start_Time: int, New_End_Time: int, New_Type: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Contest SET Name = %s, Start_Time = %s, End_Time = %s, Type = %s WHERE ID = %s",
                           (New_Name, str(New_Start_Time), str(New_End_Time), str(New_Type), str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Modify_Contest\n")
        db.close()
        return

    def Delete_Contest(self, ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Contest WHERE ID = %s", (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Delete_Contest(1)\n")

        try:
            cursor.execute("DELETE FROM Contest_Player WHERE Belong = %s", (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Delete_Contest(2)\n")

        try:
            cursor.execute("DELETE FROM Contest_Problem WHERE Belong = %s", (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Delete_Contest(3)\n")

        db.commit()
        return

    def Add_Problem_To_Contest(self, Contest_ID: int, Problem_ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Contest_Problem (Belong, Problem_ID) VALUES (%s, %s)", (str(Contest_ID), str(Problem_ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Add_Problem_To_Contest\n")
        db.commit()
        return

    def Delete_Problem_From_Contest(self, Contest_ID: int, Problem_ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Contest_Problem WHERE Belong = %s AND Problem_ID = %s", (str(Contest_ID), str(Problem_ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Delete_Problem_From_Contest\n")
        db.commit()
        return

    def Add_Player_To_Contest(self, Contest_ID: int, Username: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Contest_Player (Belong, Username) VALUES (%s, %s)", (str(Contest_ID), str(Username)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Add_Player_To_Contest\n")
        db.commit()
        return

    def Delete_Player_From_Contest(self, Contest_ID: int, Username: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Contest_Player WHERE Belong = %s AND Username = %s", (str(Contest_ID), str(Username)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ConetstManager: Delete_Player_From_Contest\n")
        db.commit()
        return

    def List_Problem_For_Contest(self, Contest_ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Problem_ID FROM Contest_Problem WHERE Belong = %s", (str(Contest_ID)))
        ret = cursor.fetchall()
        return ret

    def List_Player_For_Contest(self, Contest_ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username FROM Contest_Player WHERE Belong = %s", (str(Contest_ID)))
        ret = cursor.fetchall()
        return ret

Conetst_Manager = ConetstManager()