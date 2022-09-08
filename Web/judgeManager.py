import sys

import pymysql

from utils import *


class JudgeManager:
    """
    * ID: INT, auto_increment, PRIMARY KEY
    * Code: TEXT
    * User: TINYTEXT
    * Problem_ID: INT
    * Language: INT
    * Status: INT
    * Score: INT
    * Time: BIGINT // unix nano
    * Time_Used: INT // ms
    * Mem_Used: INT // Byte
    * Detail: MEDIUMTEXT // may exceed 64 KB
    """

    def add_judge(self, code: str, user: str, problem_id: int, language: int, time: int, share: bool):
        db = db_connect()
        cursor = db.cursor()
        data = None
        try:
            cursor.execute(
                "INSERT INTO Judge(Code, User, Problem_ID, Language, Time, Status, Share) VALUES(%s, %s, %s, %s, %s, '0', %s) RETURNING ID",
                (code, user, str(problem_id), str(language), str(time), int(share)))
            data = cursor.fetchone()[0]
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Add_Judge\n")
        db.close()
        return data


    # def add_quiz(self, user: str, problem_id: int, status: str, score: str, time: str, time_used: str, mem_used: str, detail: str):
    #     db = db_connect()
    #     cursor = db.cursor()
    #     try:
    #         cursor.execute("INSERT INTO Judge(Code, User, Problem_ID, Language, Status, Score, Time, Time_Used, Mem_Used, Detail, Share) VALUES('Quiz', %s, %s, '3', %s, %s, %s, %s, %s, '%s', '0')",
    #             (user, str(problem_id), str(status), str(score), str(time), str(time_used), str(mem_used), str(detail)))
    #         db.commit()
    #     except pymysql.Error:
    #         db.rollback()
    #         sys.stderr.write("SQL Error in JudgeManager: Add_Quiz\n")
    #     db.close()
    #     return


    def update_status(self, judge_id: int, new_status: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Judge SET Status = %s WHERE ID = %s", (str(new_status), str(judge_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Update_Status\n")
        db.close()
        return

    def update_after_judge(self, judge_id: int, new_status: int, score: int, detail: str, time_used: str,
                           mem_used: str):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute(
                "UPDATE Judge SET Status = %s, Score = %s, Detail = %s, Time_Used = %s, Mem_Used = %s WHERE ID = %s",
                (str(new_status), str(score), detail, time_used, mem_used, str(judge_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Update_After_Judge\n")
        db.close()
        return

    def query_judge(self, judge_id: int) -> dict:  # for details
        db = db_connect()
        cursor = db.cursor()
        cursor.execute(
            "SELECT ID, User, Problem_ID, Detail, Time, Time_Used, Mem_Used, Share, Status, Language, Code  FROM Judge WHERE ID = %s",
            (str(judge_id)))
        data = cursor.fetchone()
        db.close()
        if data is None:
            return {}
        ret = {'ID': int(data[0]),
               'User': str(data[1]),
               'Problem_ID': int(data[2]),
               'Detail': str(data[3]),
               'Time': int(data[4]),
               'Time_Used': int(data[5]),
               'Mem_Used': int(data[6]),
               'Share': bool(data[7]),
               'Status': str(data[8]),
               'Lang': int(data[9]),
               'Code': str(data[10])}
        return ret

    def max_id(self):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Judge")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    def judge_in_range(self, start_id: int, end_id: int):  # [{}], for page display.
        db = db_connect()
        cursor = db.cursor()
        cursor.execute(
            "SELECT ID, User, Problem_ID, Time, Time_Used, Mem_Used, Status, Language, Share FROM Judge WHERE ID >= %s and ID <= %s ORDER BY ID desc",
            (str(start_id), str(end_id)))
        data = cursor.fetchall()
        ret = []
        for d in data:
            cur = {'ID': int(d[0]),
                   'Username': str(d[1]),
                   'Problem_ID': int(d[2]),
                   'Time': int(d[3]),
                   'Time_Used': int(d[4]),
                   'Mem_Used': int(d[5]),
                   'Status': str(d[6]),
                   'Lang': int(d[7]),
                   'Share': bool(d[8])}
            ret.append(cur)
        db.close()
        return ret

    """
    def get_contest_judge(self, problem_id: int, username: str, start_time: int, end_time: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute(
            "SELECT ID, Status, Score, Time FROM Judge WHERE Problem_ID = %s AND User = %s AND Time >= %s AND Time <= %s",
            (str(problem_id), username, str(start_time), str(end_time)))
        ret = cursor.fetchall()
        db.close()
        return ret
    """

    def get_contest_judge(self, problems: list, start_time: int, end_time: int):
        if len(problems) == 0:
            return []
        db = db_connect()
        cursor = db.cursor()
        com = 'SELECT ID, User, Problem_ID, Status, Score, Time FROM Judge WHERE (Time >= %s AND Time <= %s) AND ('
        args = [str(start_time), str(end_time)]
        for i in range(len(problems)):
            if i > 0:
                com += ' OR '
            com += 'Problem_ID = %s'
            args.append(problems[i])                

        com = com + ')'
        cursor.execute(com, tuple(args))

        ret = cursor.fetchall()
        db.close()
        return ret  

    def search_judge(self, arg_submitter, arg_problem_id, arg_status, arg_lang, arg_param=None):
        db = db_connect()
        cursor = db.cursor()
        com = 'SELECT ID, User, Problem_ID, Time, Time_Used, Mem_Used, Status, Language, Share FROM Judge WHERE '
        pre = []

        if arg_problem_id is not None:
            com = com + 'Problem_ID = %s'
            pre.append(str(arg_problem_id))
        if arg_submitter is not None:
            if len(pre):
                com = com + ' AND '
            com = com + 'User = %s'
            pre.append(str(arg_submitter))
        if arg_status is not None:
            if len(pre):
                com = com + ' AND '
            com = com + 'Status = %s'
            pre.append(str(arg_status))
        if arg_lang is not None:
            if len(pre):
                com = com + ' AND '
            com = com + 'Language = %s'
            pre.append(str(arg_lang))
        if arg_param is None:
            com = com + ' ORDER BY ID asc'
        else:
            com = com + ' ORDER BY Time_Used asc'
        cursor.execute(com, tuple(pre))
        data = cursor.fetchall()
        db.close()
        ret = []
        for d in data:
            cur = {'ID': int(d[0]),
                   'Username': str(d[1]),
                   'Problem_ID': int(d[2]),
                   'Time': int(d[3]),
                   'Time_Used': int(d[4]),
                   'Mem_Used': int(d[5]),
                   'Status': str(d[6]),
                   'Lang': int(d[7]),
                   'Share': bool(d[8])}
            ret.append(cur)
        return ret

    def search_ac(self, problem_id):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute(
            "SELECT ID, User, Time_Used, Mem_Used, Language, Time FROM Judge WHERE Problem_ID = %s and Status = 2",
            (str(problem_id)))
        ret = cursor.fetchall()
        db.close()
        return ret

    def delete_judge(self, judge_id: int):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("DELETE FROM Judge WHERE  ID = %s", (str(judge_id)))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in JudgeManager: Erase_Judge\n")
        return

    def get_pending_judge(self):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Problem_ID, Code, Language FROM Judge WHERE Status = 0")
        ls = cursor.fetchall()
        if ls is None or len(ls) == 0:
            return None
        return ls[0]


Judge_Manager = JudgeManager()
