import random
import hashlib
import sys
from utils import *

def hash(Password, Salt):
    return str(hashlib.sha512((Password + str(Salt)).encode('utf-8')).hexdigest())
def randInt():
    return random.randint(3456, 89786576)

class UserManager:
    def Add_User(self, Username:str, Student_ID:str, Friendly_Name:str, Password:str, Privilege:str): # will not check whether the argument is illegal
        Salt = randInt()
        Password = hash(Password, Salt)
        db = DB_Connect()
        cursor = db.cursor()
        # print("INSERT INTO User(Username, Student_ID, Friendly_Name, Password, Salt, Privilege) VALUES(%s, %s, %s, %s, %s, %s)" % (Username, Student_ID, Friendly_Name, Password, str(Salt), Privilege))
        try:
            cursor.execute("INSERT INTO User(Username, Student_ID, Friendly_Name, Password, Salt, Privilege) VALUES(%s, %s, %s, %s, %s, %s)",
                        (Username, Student_ID, Friendly_Name, Password, str(Salt), Privilege))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in UserManager: addUser\n")
        db.close()
        return

    def Modify_User(self, Username:str, Student_ID:str, Friendly_Name:str, Password:str, Privilege:str):
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username, Student_ID, Friendly_Name, Password, Salt, Privilege FROM User WHERE Username = %s", (Username))
        data = cursor.fetchone()

        if Student_ID == '':
            Student_ID = str(data[1])
        if Friendly_Name == '':
            Friendly_Name = data[2]
        if Password == '':
            Password = data[3]
            Salt = int(data[4])
        else:
            Salt = randInt()
            Password = hash(Password, Salt)
        if Privilege == '':
            Privilege = str(data[5])

        # print("UPDATE User SET Student_ID = %s, Friendly_Name = %s, Password = %s, Salt = %s, Privilege = %s where Username = %s" % (Student_ID, Friendly_Name, Password, str(Salt), Privilege, Username))
        try:
            cursor.execute("UPDATE User SET Student_ID = %s, Friendly_Name = %s, Password = %s, Salt = %s, Privilege = %s WHERE Username = %s",
                           (Student_ID, Friendly_Name, Password, str(Salt), Privilege, Username))
            db.commit()
        except:
            db.rollback()
            sys.stderr.write("SQL Error in UserManager: ModifyUser\n")
        db.close()

    def Validate_Username(self, Username: str) -> bool:
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM User WHERE Username = %s", (Username))
        data = cursor.fetchone()
        db.close()
        return data == None

    def Check_Login(self, Username:str, Password:str) -> bool:
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Password, Salt FROM User WHERE Username = %s", (Username))
        data = cursor.fetchone()
        db.close()
        if data == None: # User not found
            return False
        h = hash(Password, int(data[1]))
        return h == data[0]

    def Get_Friendly_Name(self, Username:str) -> str: # Username must exist.
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Friendly_Name FROM User WHERE Username = %s", (Username))
        data = cursor.fetchone()
        db.close()
        return data[0]

    def Get_Student_ID(self, Username:str) -> str: # Username must exist.
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Student_ID FROM User WHERE Username = %s", (Username))
        data = cursor.fetchone()
        db.close()
        return str(data[0])

    def Get_Privilege(self, Username:str) -> int: # Username must exist.
        db = DB_Connect()
        cursor = db.cursor()
        cursor.execute("SELECT Privilege FROM User WHERE Username = %s", (Username))
        data = cursor.fetchone()
        db.close()
        return int(data[0])

    def Delete_User(self, Username: str):
        db = DB_Connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM User WHERE Username = %s", (Username))
        except:
            db.rollback()
            return
        db.close()
