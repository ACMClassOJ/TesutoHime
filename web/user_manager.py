__all__ = ('UserManager',)

import hashlib
import random
import sys
from typing import Optional

import pymysql

from web.utils import db_connect


def hash(password, salt):
    return str(hashlib.sha512((password + str(salt)).encode('utf-8')).hexdigest())


def rand_int():
    return random.randint(3456, 89786576)


class UserManager:
    @staticmethod
    def add_user(username: str, student_id: int, friendly_name: str, password: str,
                 privilege: int):  # will not check whether the argument is illegal
        salt = rand_int()
        password = hash(password, salt)
        db = db_connect()
        cursor = db.cursor()
        # print("INSERT INTO User(Username, Student_ID, Friendly_Name, Password, Salt, Privilege) VALUES(%s, %s, %s, %s, %s, %s)" % (Username, Student_ID, Friendly_Name, Password, str(Salt), Privilege))
        try:
            cursor.execute(
                "INSERT INTO User(Username, Student_ID, Friendly_Name, Password, Salt, Privilege) VALUES(%s, %s, %s, %s, %s, %s)",
                (username, student_id, friendly_name, password, salt, privilege))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in UserManager: addUser\n")
        db.close()
        return

    @staticmethod
    def modify_user(username: str, student_id: Optional['int'], friendly_name: Optional['str'],
                    password: Optional['str'], privilege: Optional['int']):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute(
            "SELECT Username, Student_ID, Friendly_Name, Password, Salt, Privilege FROM User WHERE Username = %s",
            username)
        data = cursor.fetchone()

        if student_id is None:
            student_id = data[1]
        if friendly_name is None:
            friendly_name = data[2]
        if password is None:
            password = data[3]
            salt = int(data[4])
        else:
            salt = rand_int()
            password = hash(password, salt)
        if privilege is None:
            privilege = data[5]

        # print("UPDATE User SET Student_ID = %s, Friendly_Name = %s, Password = %s, Salt = %s, Privilege = %s where Username = %s" % (Student_ID, Friendly_Name, Password, str(Salt), Privilege, Username))
        try:
            cursor.execute(
                "UPDATE User SET Student_ID = %s, Friendly_Name = %s, Password = %s, Salt = %s, Privilege = %s WHERE Username = %s",
                (student_id, friendly_name, password, salt, privilege, username))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in UserManager: ModifyUser\n")
        db.close()

    @staticmethod
    def validate_username(username: str) -> bool:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM User WHERE Username = %s", username)
        data = cursor.fetchone()
        db.close()
        return data is None

    @staticmethod
    def check_login(username: str, password: str) -> bool:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Password, Salt FROM User WHERE Username = %s", username)
        data = cursor.fetchone()
        db.close()
        if data is None:  # User not found
            return False
        h = hash(password, int(data[1]))
        return h == data[0]

    @staticmethod
    def get_friendly_name(username: str) -> str:  # Username must exist.
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Friendly_Name FROM User WHERE Username = %s", username)
        data = cursor.fetchone()
        db.close()
        return data[0]

    @staticmethod
    def get_username(username: str) -> Optional[str]:  # Username must exist.
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username FROM User WHERE Username = %s", username)
        data = cursor.fetchone()
        db.close()
        if data is None:
            return None
        return str(data[0])

    @staticmethod
    def get_student_id(username: str) -> Optional[str]:  # Username must exist.
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Student_ID FROM User WHERE Username = %s", username)
        data = cursor.fetchone()
        db.close()
        if data is None:
            return None
        return str(data[0])

    @staticmethod
    def get_privilege(username: str) -> int:  # Username must exist.
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Privilege FROM User WHERE Username = %s", username)
        data = cursor.fetchone()
        db.close()
        return int(data[0])

    @staticmethod
    def delete_user(username: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM User WHERE Username = %s", username)
        except pymysql.Error:
            db.rollback()
            return
        db.close()

    @staticmethod
    def has_user(username: str) -> bool:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM User WHERE Username = %s", username)
        data = cursor.fetchone()
        db.close()
        return data is not None
