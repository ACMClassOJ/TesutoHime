import sys
from utils import *


class ProblemManager:
    def add_problem(self, title: str, description: str, problem_input: str, problem_output: str, example_input: str,
                    example_output: str, data_range: str, release_time: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO Problem(ID, Title, Description, Input, Output, Example_Input, Example_Output, Data_Range, Release_Time) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (self.get_max_id() + 1, title, description, problem_input, problem_output, example_input, example_output, data_range,
                 release_time))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Add_Problem\n")
        db.close()
        return

    def modify_problem(self, problem_id: int, title: str, description: str, problem_input: str, problem_output: str,
                       example_input: str, example_output: str, data_range: str, release_time: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute(
                "UPDATE Problem SET Title = %s, Description = %s, Input = %s, Output = %s, Example_Input = %s, Example_Output = %s, Data_Range = %s, Release_Time = %s WHERE ID = %s",
                (title, description, problem_input, problem_output, example_input, example_output, data_range,
                 release_time, problem_id))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Modify_Problem\n")
            db.close()
        return

    def get_problem(self, problem_id: int) -> dict:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM Problem WHERE ID = %s", (str(problem_id)))
        data = cursor.fetchone()
        db.close()
        if data is None:
            return {}
        ret = {'ID': int(data[0]),
               'Title': str(data[1]),
               'Description': str(data[2]),
               'Input': str(data[3]),
               'Output': str(data[4]),
               'Example_Input': str(data[5]),
               'Example_Output': str(data[6]),
               'Data_Range': str(data[7]),
               'Release_Time': int(data[8]),
               'Flag_Count': int(data[9])}
        return ret

    def lock_problem(self, problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Problem SET Flag_Count = 1 WHERE ID = %s", (str(problem_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Lock_Problem\n")
        db.close()

    def unlock_problem(self, problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Problem SET Flag_Count = 0 WHERE ID = %s", (str(problem_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Unlock_Problem\n")
        db.close()

    def get_title(self, problem_id: int) -> str:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Title FROM Problem WHERE ID = %s", (str(problem_id)))
        data = cursor.fetchone()
        db.close()
        if data is None:
            return ""
        return str(data[0])

    def in_contest(self, problem_id: int) -> bool:  # return True when this Problem is in a Contest or Homework
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Flag_Count FROM Problem WHERE ID = %s", (str(problem_id)))
        data = cursor.fetchone()
        db.close()
        if data is None:
            return False
        return int(data[0]) != 0

    def get_max_id(self) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Problem WHERE ID < 11000")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])
        
    def get_problem_count(self, now_time: int) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(ID) FROM Problem WHERE Problem.Release_Time <= " + str(now_time))
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    def get_problem_count_admin(self) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(ID) FROM Problem")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    def get_real_max_id(self) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Problem")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    def get_release_time(self, problem_id: int) -> int:
        db = db_connect()
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Release_Time FROM Problem WHERE ID = %s", (str(problem_id)))
        ret = cursor.fetchone()
        db.close()
        if ret is None:
            return 0
        return int(ret[0])

    def problem_in_range(self, start_id: int, end_id: int, time_now: int, is_admin: bool):
        db = db_connect()
        cursor = db.cursor()
        if not is_admin:
            cursor.execute("SELECT ID, Title FROM Problem WHERE ID >= %s and ID <= %s and Release_Time <= %s",
                           (str(start_id), str(end_id), str(time_now)))
        else:
            cursor.execute("SELECT ID, Title FROM Problem WHERE ID >= %s and ID <= %s", (str(start_id), str(end_id)))
        ret = cursor.fetchall()
        db.close()
        return ret
        
    def problem_in_page_autocalc(self, page: int, problem_num_per_page: int, time_now: int, is_admin: bool):
        db = db_connect()
        cursor = db.cursor()
        problem_num_start = (page - 1) * problem_num_per_page + 1
        if not is_admin:
            cursor.execute("SELECT ID, Title FROM Problem WHERE Release_Time <= " + str(time_now) + " LIMIT "
                           + str(problem_num_start) + "," + str(problem_num_per_page))
        else:
            cursor.execute("SELECT ID, Title FROM Problem LIMIT " + str(problem_num_start) + "," + str(problem_num_per_page))
        ret = cursor.fetchall()
        db.close()
        return ret

    def delete_problem(self, problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Problem WHERE ID = %s", (str(problem_id)))
        except pymysql.Error:
            db.rollback()
            return
        db.close()


Problem_Manager = ProblemManager()
