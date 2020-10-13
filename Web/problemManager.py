import sys
from utils import *

class ProblemManager:
    def Add_Problem(self, Title:str, Description:str, Input:str, Output:str, Example_Input:str, Example_Output:str, Data_Range:str, Release_Time:int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Problem(Title, Description, Input, Output, Example_Input, Example_Output, Data_Range, Release_Time) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)",
                           (Title, Description, Input, Output, Example_Input, Example_Output, Data_Range, Release_Time))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Add_Problem\n")
            db.close()
        return

    def Modify_Problem(self, ID:int, Title:str, Description:str, Input:str, Output:str, Example_Input:str, Example_Output:str, Data_Range:str, Release_Time:int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Problem SET Title = %s, Description = %s, Input = %s, Output = %s, Example_Input = %s, Example_Output = %s, Data_Range = %s, Release_Time = %s WHERE ID = %s",
                           (Title, Description, Input, Output, Example_Input, Example_Output, Data_Range, Release_Time, ID))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Modify_Problem\n")
            db.close()
        return

    def Get_Problem(self, ID:int)->dict:
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Problem WHERE ID = %s", (str(ID)))
        data = cursor.fetchone()
        db.close()
        if data == None:
            return {}
        ret = {}
        ret['ID'] = int(data[0])
        ret['Title'] = str(data[1])
        ret['Description'] = str(data[2])
        ret['Input'] = str(data[3])
        ret['Output'] = str(data[4])
        ret['Example_Input'] = str(data[5])
        ret['Example_Output'] = str(data[6])
        ret['Data_Range'] = str(data[7])
        ret['Release_Time'] = int(data[8])
        ret['Flag_Count'] = int(data[9])
        return ret

    def Lock_Problem(self, ID:int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Problem SET Flag_Count = 1 WHERE ID = %s", (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Lock_Problem\n")
        db.close()

    def Unlock_Problem(self, ID:int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Problem SET Flag_Count = 0 WHERE ID = %s", (str(ID)))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Unlock_Problem\n")
        db.close()

    def Get_Title(self, ID:int) -> str:
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Title FROM Problem WHERE ID = %s", (str(ID)))
        data = cursor.fetchone()
        db.close()
        if data == None:
            return ""
        return str(data[0])

    def In_Contest(self, ID: int) -> bool: # return True when this Problem is in a Contest or Homework
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Flag_Count FROM Problem WHERE ID = %s", (str(ID)))
        data = cursor.fetchone()
        db.close()
        if data == None:
            return False
        return int(data[0]) != 0

    def Get_Max_ID(self) -> int:
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Problem")
        data = cursor.fetchone()
        db.close()
        return data[0]

    def Get_Release_Time(self, Problem_ID: int) -> int:
        db = DB_Connect()
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Release_Time FROM Problem WHERE ID = %s", (str(Problem_ID)))
        ret = cursor.fetchone()
        db.close()
        if ret == None:
            return 0
        return int(ret[0])

    def Problem_In_Range(self, startID: int, endID: int, timeNow: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Title FROM Problem WHERE ID >= %s and ID <= %s and Release_Time <= %s", (str(startID), str(endID), str(timeNow)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def Delete_Problem(self, ID: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Problem WHERE ID = %s", (str(ID)))
        except:
            db.rollback()
            return
        db.close()

Problem_Manager = ProblemManager()