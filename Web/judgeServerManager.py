import sys
import random
from utils import *

class JudgeServerManager:
    def Add_Judge_Server(self, Address: str, Secret: str, Friendly_Name: str, Detail: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Judge_Server (Address, Secret_Key, Friendly_Name, Detail) VALUES (%s, %s, %s, %s)",
                           (Address, Secret, Friendly_Name, Detail))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeServerManager: Add_Judge_Server\n")
        db.close()
        return

    # def Modify_Server_Detail(self):

    def Remove_Judge_Server(self, Secret: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Judge_Server WHERE Secret_Key = %s", (Secret))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeServerManager: Remove_Judge_Server\n")
        db.close()
        return

    def Flush_Busy(self, Secret: str, New_State: bool, Current_Task: int = -1):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Judge_Server SET Busy = %s, Current_Task = %s WHERE Secret_Key = %s", (str(int(New_State)), Current_Task, Secret))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeServerManager: Flush_Busy\n")
        db.close()
        return

    def Flush_Heartbeat(self, Secret: str, CurTime: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Judge_Server SET Last_Seen_Time = %s WHERE Secret_Key = %s", (str(CurTime), Secret))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeServerManager: Flush_Heartbeat\n")
        db.close()
        return

    def Check_Secret(self, Secret: str):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID FROM Judge_Server WHERE Secret_Key = %s", (Secret))
        ret = cursor.fetchall()
        db.close()
        return ret != None

    def Get_Online_Server_List(self, MinTime: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Secret_Key FROM Judge_Server WHERE Last_Seen_Time >= %s", (str(MinTime)))
        data = cursor.fetchall()
        db.close()
        return data

    def Set_Offline(self, Secret: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Judge_Server SET Last_Seen_Time = %s WHERE Secret_Key = %s", ('0', Secret))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeServerManager: Set_Offline\n")
        db.close()
        return

    def Get_Standby_Server(self, MinTime: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Address, Secret_Key FROM Judge_Server WHERE Last_Seen_Time >= %s AND Busy = %s", (str(MinTime), '0'))
        ret = cursor.fetchall()
        db.close()
        if ret == None or len(ret) == 0:
            return None
        st = random.randint(0, len(ret) - 1)
        for i in range(st, st + len(ret)):
            if Ping(ret[i % st][0]):
                return ret[i % st]
            else:
                self.Set_Offline(ret[i % st][0])
        return None

    def Get_Failure_Task(self):
        db = DB_Connect()
        cursor = db.cursor()
        minTime = UnixNano() - JudgeConfig.Max_Duration
        cursor.execute("SELECT Current_Task FROM Judge_Server WHERE Last_Seen_Time < %s", (str(minTime), ))
        ret = cursor.fetchall()
        db.close()
        if ret == None or len(ret) == 0:
            return None
        return ret

    def Get_Server_List(self):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Last_Seen_Time, Busy, Friendly_Name, Detail FROM Judge_Server")
        ls = cursor.fetchall()
        db.close()
        ret = []
        for x in ls:
            temp = {}
            temp['Status'] = bool(int(x[0]) > UnixNano() - JudgeConfig.Max_Duration)
            temp['Name'] = x[2]
            temp['System'] = x[3].split('\n')[0]
            temp['Last_Seen_Time'] = Readable_Time(UnixNano())
            temp['Busy'] = x[1]
            temp['Provider'] = x[3].split('\n')[1]
            ret.append(temp)
        return ret

JudgeServer_Manager = JudgeServerManager()