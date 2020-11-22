import sys
from utils import *


class DiscussManager:
    def add_discuss(self, problem_id: int, username: str, data: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Discuss(Problem_ID, Username, Data, Time) VALUES(%s, %s, %s, %s)",
                           (problem_id, username, data, UnixNano()))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Add_Discuss\n")
        db.close()
        return

    def modify_discuss(self, discuss_id: int, new_data: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Discuss SET DATA = %s WHERE ID = %s", (new_data, discuss_id))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Modify_Discuss\n")
        db.close()
        return

    def get_author(self, discuss_id: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username FROM Discuss WHERE ID = %s", discuss_id)
        ret = cursor.fetchone()
        return ret[0]

    def get_discuss_for_problem(self, problem_id: int):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Username, DATA, Time FROM Discuss WHERE Problem_ID = %s", problem_id)
        ret = cursor.fetchall()
        db.close()
        return ret

    def delete_discuss(self, discuss_id: int):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Discuss WHERE ID = %s", discuss_id)
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Erase_Discuss\n")
        db.close()
        return


Discuss_Manager = DiscussManager()
