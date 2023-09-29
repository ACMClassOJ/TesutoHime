__all__ = ('DiscussManager',)

import sys

import pymysql

from web.utils import db_connect, unix_nano


class DiscussManager:
    @staticmethod
    def add_discuss(problem_id: int, username: str, data: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Discuss(Problem_ID, Username, Data, Time) VALUES(%s, %s, %s, %s)",
                           (problem_id, username, data, unix_nano()))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Add_Discuss\n")
        db.close()
        return

    @staticmethod
    def modify_discuss(discuss_id: int, new_data: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Discuss SET DATA = %s WHERE ID = %s", (new_data, discuss_id))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Modify_Discuss\n")
        db.close()
        return

    @staticmethod
    def get_author(discuss_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username FROM Discuss WHERE ID = %s", discuss_id)
        ret = cursor.fetchone()
        return ret[0]

    @staticmethod
    def get_discuss_for_problem(problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Username, DATA, Time FROM Discuss WHERE Problem_ID = %s", problem_id)
        ret = cursor.fetchall()
        db.close()
        return ret

    @staticmethod
    def delete_discuss(discuss_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Discuss WHERE ID = %s", discuss_id)
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in DiscussManager: Erase_Discuss\n")
        db.close()
        return
