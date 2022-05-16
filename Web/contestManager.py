import sys
from utils import *


class ContestManager:
    def create_contest(self, id: int, name: str, start_time: int, end_time: int, contest_type: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Contest (ID, Name, Start_Time, End_Time, Type) VALUES (%s, %s, %s, %s, %s)",
                           (id, name, start_time, end_time, contest_type))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Create_Contest\n")
        db.close()
        return

    def modify_contest(self, contest_id: int, new_name: str, new_start_time: int, new_end_time: int,
                       new_contest_type: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Contest SET Name = %s, Start_Time = %s, End_Time = %s, Type = %s WHERE ID = %s",
                           (new_name, new_start_time, new_end_time, new_contest_type, contest_id))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Modify_Contest\n")
        db.close()
        return

    def delete_contest(self, contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Contest WHERE ID = %s", (str(contest_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Delete_Contest(1)\n")

        try:
            cursor.execute("DELETE FROM Contest_Player WHERE Belong = %s", (str(contest_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Delete_Contest(2)\n")

        try:
            cursor.execute("DELETE FROM Contest_Problem WHERE Belong = %s", (str(contest_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Delete_Contest(3)\n")

        db.close()
        return

    def add_problem_to_contest(self, contest_id: int, problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Contest_Problem (Belong, Problem_ID) VALUES (%s, %s)",
                           (str(contest_id), str(problem_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Add_Problem_To_Contest\n")
        db.close()
        return

    def delete_problem_from_contest(self, contest_id: int, problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Contest_Problem WHERE Belong = %s AND Problem_ID = %s",
                           (str(contest_id), str(problem_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Delete_Problem_From_Contest\n")
        db.close()
        return

    def add_player_to_contest(self, contest_id: int, username: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Contest_Player (Belong, Username) VALUES (%s, %s)",
                           (str(contest_id), str(username)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Add_Player_To_Contest\n")
        db.close()
        return

    def check_problem_in_contest(self, contest_id: int, problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Problem_ID FROM Contest_Problem WHERE Belong = %s AND Problem_ID = %s", (contest_id, problem_id))
        ret = cursor.fetchall()
        db.close()
        return len(ret) != 0

    def check_player_in_contest(self, contest_id: int, username: str):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT tempID FROM Contest_Player WHERE Belong = %s AND Username = %s", (contest_id, username))
        ret = cursor.fetchall()
        db.close()
        return len(ret) != 0
    
    def get_unfinished_exam_info_for_player(self, username: str, cur_time: int) -> (int, bool):
        """
            return exam_id, is_exam_started 
        """

        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Start_Time FROM Contest WHERE Type = 2 AND %s <= End_Time ORDER BY ID DESC", (str(cur_time)))
        unfinished_exam = cursor.fetchall()
        db.close()
        
        for exam in unfinished_exam:
            if self.check_player_in_contest(exam[0], username):
            	return exam[0], (cur_time >= int(exam[1]))

        return -1, False

    def delete_player_from_contest(self, contest_id: int, username: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Contest_Player WHERE Belong = %s AND Username = %s",
                           (str(contest_id), str(username)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Delete_Player_From_Contest\n")
        db.close()
        return

    def list_contest(self, contest_type: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Name, Start_Time, End_Time, Type FROM Contest WHERE Type = %s ORDER BY ID DESC",
                       (contest_type))
        ret = cursor.fetchall()
        db.close()
        return ret

    def list_contest_and_exam(self):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Name, Start_Time, End_Time, Type FROM Contest WHERE Type = 0 OR Type = 2 ORDER BY ID DESC")
        ret = cursor.fetchall()
        db.close()
        return ret

    def get_time(self, contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Start_Time, End_Time FROM Contest WHERE ID = %s", (str(contest_id)))
        ret = cursor.fetchone()
        db.close()
        return int(ret[0]), int(ret[1])

    def list_problem_for_contest(self, contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Problem_ID FROM Contest_Problem WHERE Belong = %s", (str(contest_id)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def list_player_for_contest(self, contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username FROM Contest_Player WHERE Belong = %s", (str(contest_id)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def get_title(self, contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Name FROM Contest WHERE ID = %s", (str(contest_id)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def get_contest(self, contest_id: int) -> dict:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Contest WHERE ID = %s", (str(contest_id)))
        data = cursor.fetchone()
        db.close()
        if data is None:
            return {}
        ret = {'ID': int(data[0]),
               'Name': str(data[1]),
               'Start_Time': int(data[2]),
               'End_Time': int(data[3]),
               'Type': int(data[4])}
        return ret

    def get_max_id(self) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Contest")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0]) 


Contest_Manager = ContestManager()
