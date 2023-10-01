import sys
from datetime import datetime
from http.client import BAD_REQUEST

import pymysql
from flask import abort

from commons.models import ContestProblem, JudgeRecord2, Problem
from web.const import Privilege
from web.session_manager import SessionManager
from web.utils import SqlSession, db_connect, unix_nano


class ProblemManager:
    @staticmethod
    def add_problem() -> int:
        problem_id = ProblemManager.get_max_id() + 1
        with SqlSession() as db:
            problem = Problem()
            problem.id = problem_id
            problem.release_time = 253402216962
            db.add(problem)
            db.commit()
        return problem_id

    @staticmethod
    def modify_problem_description(problem_id: int, description: str, problem_input: str, problem_output: str,
                       example_input: str, example_output: str, data_range: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute(
                "UPDATE Problem SET Description = %s, Input = %s, Output = %s, Example_Input = %s, Example_Output = %s, Data_Range = %s WHERE ID = %s",
                (description, problem_input, problem_output, example_input, example_output, data_range,
                 problem_id))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Modify_Problem\n")
            db.close()
        return

    @staticmethod
    def modify_problem(problem_id: int, title: str, release_time: int, problem_type: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute(
                "UPDATE Problem SET Title = %s, Release_Time = %s, Problem_Type = %s WHERE ID = %s",
                (title, release_time, problem_type, problem_id))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Modify_Problem\n")
            db.close()
        return

    @staticmethod
    def hide_problem(problem_id: int):
        with SqlSession() as db:
            db.query(Problem).where(Problem.id == problem_id).one().release_time = 253402216962
            db.commit()

    @staticmethod
    def show_problem(problem_id: int):
        now = datetime.now().timestamp()
        with SqlSession() as db:
            db.query(Problem).where(Problem.id == problem_id).one().release_time = now - 1
            db.commit()

    @staticmethod
    def get_problem(problem_id: int) -> dict:
        with SqlSession(expire_on_commit=False) as db:
            return db \
                .query(Problem) \
                .where(Problem.id == problem_id) \
                .one_or_none()

    @staticmethod
    def modify_problem_limit(problem_id: int, limit: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Problem SET Limits = %s WHERE ID = %s", (limit, str(problem_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ProblemManager: Modify_Problem_Limit\n")
        db.close()

    @staticmethod
    def get_title(problem_id: int) -> str:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Title FROM Problem WHERE ID = %s", (str(problem_id)))
        data = cursor.fetchone()
        db.close()
        if data is None:
            return ""
        return str(data[0])

    @staticmethod
    def get_problem_type(problem_id: int) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Problem_Type FROM Problem WHERE ID = %s", (str(problem_id)))
        data = cursor.fetchone()
        db.close()
        if data is None:
            return ""
        return int(data[0])

    @staticmethod
    def get_max_id() -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Problem WHERE ID < 11000")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    @staticmethod
    def get_problem_count(now_time: int) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(ID) FROM Problem WHERE Problem.Release_Time <= %s", (str(now_time)))
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    @staticmethod
    def get_problem_count_under_11000(now_time: int) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(ID) FROM Problem WHERE Problem.Release_Time <= %s AND Problem.ID < 11000", (str(now_time)))
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    @staticmethod
    def get_problem_count_admin() -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(ID) FROM Problem")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    @staticmethod
    def get_problem_count_under_11000_admin() -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(ID) FROM Problem WHERE Problem.ID < 11000")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    @staticmethod
    def get_real_max_id() -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Problem")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])


    @staticmethod
    def should_show(problem: Problem) -> bool:
        return problem is not None and \
            (problem.release_time <= unix_nano() or SessionManager.get_privilege() >= Privilege.ADMIN)

    @staticmethod
    def problem_in_page_autocalc(page: int, problem_num_per_page: int, time_now: int, is_admin: bool):
        db = db_connect()
        cursor = db.cursor()
        problem_num_start = (page - 1) * problem_num_per_page
        if not is_admin:
            cursor.execute("SELECT ID, Title, Problem_Type FROM Problem WHERE Release_Time <= %s ORDER BY ID LIMIT %s, %s" , (str(time_now), int(problem_num_start), int(problem_num_per_page)))
        else:
            cursor.execute("SELECT ID, Title, Problem_Type FROM Problem ORDER BY ID LIMIT %s, %s", (int(problem_num_start), int(problem_num_per_page)))
        ret = cursor.fetchall()
        db.close()
        return ret

    @staticmethod
    def search_problem(time_now: int, is_admin: bool,
                       arg_problem_id, arg_problem_name_keyword, arg_problem_type, arg_contest_id):
        db = db_connect()
        cursor = db.cursor()
        com = 'SELECT ID, Title, Problem_Type FROM Problem WHERE '
        pre = []

        if not is_admin:
            com = com + 'Release_Time <= %s'
            pre.append(str(time_now))
        if arg_problem_id is not None:
            if len(pre):
                com = com + ' AND '
            com = com + 'ID = %s'
            pre.append(str(arg_problem_id))
        if arg_problem_type is not None:
            if len(pre):
                com = com + ' AND '
            com = com + 'Problem_Type = %s'
            pre.append(str(arg_problem_type))
        if arg_problem_name_keyword is not None:
            if len(pre):
                com = com + ' AND '
            com = com + 'INSTR(TITLE, %s) > 0'
            pre.append(str(arg_problem_name_keyword))
        if is_admin and len(pre) == 0:
            com = 'SELECT ID, Title, Problem_Type FROM Problem'
        com = com + ' ORDER BY ID'

        cursor.execute(com, tuple(pre))
        problem_list = cursor.fetchall()
        ret = []
        db.close()

        contest_problem_table = dict()

        if arg_contest_id is not None:
            db = db_connect()
            cursor = db.cursor()
            cursor.execute("SELECT Problem_ID FROM Contest_Problem WHERE Belong = %s", (str(arg_contest_id)))
            contest_problem_id_list = cursor.fetchall()
            db.close()

            for sql_row in contest_problem_id_list:
                contest_problem_table[sql_row[0]] = True

        for problem in problem_list:
            if arg_contest_id is None or problem[0] in contest_problem_table:
                ret.append(problem)

        return ret


    @staticmethod
    def delete_problem(problem_id: int):
        with SqlSession() as db:
            submission_count = db.query(JudgeRecord2.id).where(JudgeRecord2.problem_id == problem_id).count()
            contest_count = db.query(ContestProblem.id).where(ContestProblem.problem_id == problem_id).count()
            if submission_count > 0 or contest_count > 0:
                abort(BAD_REQUEST)
            problem = db.query(Problem).where(Problem.id == problem_id).one_or_none()
            db.delete(problem)
            db.commit()
