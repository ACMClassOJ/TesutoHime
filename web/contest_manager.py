__all__ = ('ContestManager',)

import sys
from datetime import datetime
from functools import cmp_to_key
from typing import List, Optional, Tuple

import pymysql
from sqlalchemy.orm import defer, selectinload

from commons.models import Contest, JudgeRecord2, JudgeStatus, User
from web.contest_cache import ContestCache
from web.reference_manager import ReferenceManager
from web.utils import SqlSession, db_connect, regularize_string, unix_nano


class ContestManager:
    @staticmethod
    def create_contest(id: int, name: str, start_time: int, end_time: int, contest_type: int,
                       ranked: bool, rank_penalty: bool, rank_partial_score: bool):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO Contest (ID, Name, Start_Time, End_Time, Type, Ranked, Rank_Penalty, Rank_Partial_Score) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (id, name, start_time, end_time, contest_type, ranked, rank_penalty, rank_partial_score))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Create_Contest\n")
        db.close()
        return

    @staticmethod
    def modify_contest(contest_id: int, new_name: str, new_start_time: int, new_end_time: int,
                       new_contest_type: int,
                       ranked: bool, rank_penalty: bool, rank_partial_score: bool):
        db = db_connect()
        cursor = db.cursor()
        try:
            cursor.execute("UPDATE Contest SET Name = %s, Start_Time = %s, End_Time = %s, Type = %s, Ranked = %s, Rank_Penalty = %s, Rank_Partial_Score = %s WHERE ID = %s",
                           (new_name, new_start_time, new_end_time, new_contest_type, ranked, rank_penalty, rank_partial_score, contest_id))
            db.commit()
        except pymysql.Error:
            db.rollback()
            sys.stderr.write("SQL Error in ContestManager: Modify_Contest\n")
        db.close()
        return

    @staticmethod
    def delete_contest(contest_id: int):
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

    @staticmethod
    def add_problem_to_contest(contest_id: int, problem_id: int):
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

    @staticmethod
    def delete_problem_from_contest(contest_id: int, problem_id: int):
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

    @staticmethod
    def add_player_to_contest(contest_id: int, username: str):
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

    @staticmethod
    def check_problem_in_contest(contest_id: int, problem_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Problem_ID FROM Contest_Problem WHERE Belong = %s AND Problem_ID = %s", (contest_id, problem_id))
        ret = cursor.fetchall()
        db.close()
        return len(ret) != 0

    @staticmethod
    def check_player_in_contest(contest_id: int, username: str):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT tempID FROM Contest_Player WHERE Belong = %s AND Username = %s", (contest_id, username))
        ret = cursor.fetchall()
        db.close()
        return len(ret) != 0

    @staticmethod
    def get_unfinished_exam_info_for_player(username: str, cur_time: int) -> Tuple[int, bool]:
        """
            return exam_id, is_exam_started
        """

        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT ID, Start_Time FROM Contest WHERE Type = 2 AND %s <= End_Time ORDER BY ID DESC", (str(cur_time)))
        unfinished_exam = cursor.fetchall()
        db.close()

        for exam in unfinished_exam:
            if ContestManager.check_player_in_contest(exam[0], username):
                return exam[0], (cur_time >= int(exam[1]))

        return -1, False

    @staticmethod
    def delete_player_from_contest(contest_id: int, username: str):
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

    @staticmethod
    def get_status(contest: Contest, time: Optional[int] = None) -> str:
        # Please ensure stability of these strings; they are more like enum values than UI strings.
        # They are compared with in jinja templates.
        if time is None: time = unix_nano()
        if time < contest.start_time:
            return 'Pending'
        elif time > contest.end_time:
            return 'Finished'
        else:
            return 'Going On'

    @staticmethod
    def list_contest(types: List[int], page: int, num_per_page: int) -> Tuple[int, List[Contest]]:
        with SqlSession(expire_on_commit=False) as db:
            limit = num_per_page
            offset = (page - 1) * num_per_page
            query = db \
                .query(Contest) \
                .where(Contest.type.in_(types))
            count = query.count()
            this_page = query \
                .order_by(Contest.id.desc()) \
                .limit(limit).offset(offset) \
                .all()
            return count, this_page

    @staticmethod
    def get_time(contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Start_Time, End_Time FROM Contest WHERE ID = %s", (str(contest_id)))
        ret = cursor.fetchone()
        db.close()
        return int(ret[0]), int(ret[1])

    @staticmethod
    def list_problem_for_contest(contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Problem_ID FROM Contest_Problem WHERE Belong = %s", (str(contest_id)))
        ret = cursor.fetchall()
        db.close()
        return [x[0] for x in ret]

    @staticmethod
    def list_player_for_contest(contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Username FROM Contest_Player WHERE Belong = %s", (str(contest_id)))
        ret = cursor.fetchall()
        db.close()
        return [x[0] for x in ret]

    @staticmethod
    def get_title(contest_id: int):
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Name FROM Contest WHERE ID = %s", (str(contest_id)))
        ret = cursor.fetchall()
        db.close()
        return ret

    @staticmethod
    def get_contest_for_board(contest_id: int) -> Optional[Contest]:
        with SqlSession(expire_on_commit=False) as db:
            return db \
                .query(Contest) \
                .where(Contest.id == contest_id) \
                .options(selectinload(Contest.players)) \
                .one_or_none()

    @staticmethod
    def get_contest(contest_id: int) -> Optional[Contest]:
        with SqlSession(expire_on_commit=False) as db:
            return db \
                .query(Contest) \
                .where(Contest.id == contest_id) \
                .one_or_none()

    @staticmethod
    def get_max_id() -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT MAX(ID) FROM Contest")
        data = cursor.fetchone()
        db.close()
        if data[0] is None:
            return 0
        return int(data[0])

    @staticmethod
    def get_contest_type(contest_id: int) -> int:
        db = db_connect()
        cursor = db.cursor()
        cursor.execute("SELECT Type FROM Contest WHERE ID = %s",
                       (str(contest_id)))
        type = cursor.fetchone()
        db.close()
        if type[0] is None:
            return 0
        return int(type[0])

    @staticmethod
    def get_scores(contest: Contest) -> List[dict]:
        start_time = contest.start_time
        end_time = contest.end_time
        problems = ContestManager.list_problem_for_contest(contest.id)
        players: List[User] = contest.players

        data = ContestCache.get(contest.id)
        if data is not None:
            return data

        data = [
            {
                'score': 0,
                'penalty': 0,
                'ac_count': 0,
                'friendly_name': user.friendly_name,
                'problems': [
                    {
                        'score': 0,
                        'count': 0,
                        'pending_count': 0,
                        'accepted': False,
                    } for _ in problems
                ],
                'realname': ReferenceManager.Query_Realname(user.student_id),
                'student_id': user.student_id,
                'username': user.username,
            } for user in players
        ]
        username_to_num = dict(map(lambda entry: [regularize_string(entry[1].username), entry[0]], enumerate(players)))
        problem_to_num = dict(map(lambda entry: [entry[1], entry[0]], enumerate(problems)))

        with SqlSession() as db:
            submits = db \
                .query(JudgeRecord2) \
                .options(defer(JudgeRecord2.details), defer(JudgeRecord2.message)) \
                .where(JudgeRecord2.problem_id.in_(problems)) \
                .where(JudgeRecord2.username.in_([ x.username for x in players ])) \
                .where(JudgeRecord2.created >= datetime.fromtimestamp(start_time)) \
                .where(JudgeRecord2.created < datetime.fromtimestamp(end_time)) \
                .all()
        for submit in submits:
            username = submit.username
            problem_id = submit.problem_id
            status = submit.status
            score = submit.score
            submit_time = submit.created.timestamp()

            if regularize_string(username) not in username_to_num:
                continue

            rank = username_to_num[regularize_string(username)]
            problem_index = problem_to_num[problem_id]
            user_data = data[rank]
            problem = user_data['problems'][problem_index]

            if problem['accepted'] == True:
                continue
            max_score = problem['score']
            is_ac = status == JudgeStatus.accepted
            submit_count = problem['count']

            if int(score) > max_score:
                user_data['score'] -= max_score
                max_score = int(score)
                user_data['score'] += max_score

            if is_ac:
                problem['accepted'] = True
                user_data['ac_count'] += 1
                user_data['penalty'] += (int(submit_time) - start_time + submit_count * 1200) // 60

            if status in [JudgeStatus.pending, JudgeStatus.compiling, JudgeStatus.judging]:
                problem['pending_count'] += 1
            else:
                submit_count += 1

            problem['score'] = max_score
            problem['count'] = submit_count
            problem['accepted'] = is_ac

        ContestCache.put(contest.id, data)
        return data

    @staticmethod
    def get_board_view(contest: Contest) -> List[dict]:
        scores = ContestManager.get_scores(contest)
        if not contest.ranked:
            return sorted(scores, key=lambda x: x['friendly_name'])

        key = 'score' if contest.rank_partial_score else 'ac_count'
        scores.sort(key=cmp_to_key(lambda x, y: y[key] - x[key] if x[key] != y[key] else x['penalty'] - y['penalty']))
        for i, player in enumerate(scores):
            player['rank'] = i + 1
            if i > 0 and player[key] == scores[i - 1][key]:
                if contest.rank_penalty:
                    if player['penalty'] != scores[i - 1]['penalty']:
                        continue
                player['rank'] = scores[i - 1]['rank']

        return scores
