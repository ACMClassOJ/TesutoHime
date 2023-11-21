__all__ = ('ContestManager',)

import sys
from datetime import datetime
from functools import cmp_to_key
from typing import List, Optional, Tuple

from sqlalchemy.orm import defer, selectinload

from commons.models import Contest, JudgeRecord2, JudgeStatus, User, ContestPlayer, ContestProblem
from web.contest_cache import ContestCache
from web.realname_manager import RealnameManager
from web.utils import SqlSession, regularize_string, unix_nano

from sqlalchemy import update, select, delete, insert, func, join


class ContestManager:
    @staticmethod
    def create_contest(id: int, name: str, start_time: int, end_time: int, contest_type: int,
                       ranked: bool, rank_penalty: bool, rank_partial_score: bool):
        try:
            contest = Contest(id=id,
                              name=name,
                              start_time=start_time,
                              end_time=end_time,
                              type=contest_type,
                              ranked=ranked,
                              rank_penalty=rank_penalty,
                              rank_partial_score=rank_partial_score)
            with SqlSession.begin() as db:
                db.add(contest)
        except:
            sys.stderr.write("Error in ContestManager: Create_Contest\n")

    @staticmethod
    def modify_contest(contest_id: int, new_name: str, new_start_time: int, new_end_time: int,
                       new_contest_type: int,
                       ranked: bool, rank_penalty: bool, rank_partial_score: bool):
        try:
            stmt = update(Contest).where(Contest.id == contest_id).values(
                name=new_name,
                start_time=new_start_time,
                end_time=new_end_time,
                type=new_contest_type,
                ranked=ranked,
                rank_penalty=rank_penalty,
                rank_partial_score=rank_partial_score
            )
            with SqlSession.begin() as db:
                db.execute(stmt)
        except:
            sys.stderr.write("Error in ContestManager: Modify_Contest\n")

    @staticmethod
    def delete_contest(contest_id: int):
        try:
            with SqlSession.begin() as db:
                db.execute(delete(ContestPlayer).where(
                    ContestPlayer.c.Belong == contest_id))
                db.execute(delete(ContestProblem).where(
                    ContestProblem.contest_id == contest_id))
                db.execute(delete(Contest).where(Contest.id == contest_id))
        except:
            sys.stderr.write("Error in ContestManager: Delete_Contest\n")

    @staticmethod
    def add_problem_to_contest(contest_id: int, problem_id: int):
        try:
            with SqlSession.begin() as db:
                db.add(ContestProblem(contest_id=contest_id, problem_id=problem_id))
        except:
            sys.stderr.write("Error in ContestManager: Add_Problem_To_Contest\n")

    @staticmethod
    def delete_problem_from_contest(contest_id: int, problem_id: int):
        try:
            stmt = delete(ContestProblem) \
                .where(ContestProblem.contest_id == contest_id) \
                .where(ContestProblem.problem_id == problem_id)
            with SqlSession.begin() as db:
                db.execute(stmt)
        except:
            sys.stderr.write("Error in ContestManager: Delete_Problem_From_Contest\n")

    @staticmethod
    def add_player_to_contest(contest_id: int, username: str):
        try:
            stmt = insert(ContestPlayer).values(
                Belong=contest_id, Username=username)
            with SqlSession.begin() as db:
                db.execute(stmt)
        except:
            sys.stderr.write("Error in ContestManager: Add_Player_To_Contest\n")

    @staticmethod
    def check_problem_in_contest(contest_id: int, problem_id: int):
        stmt = select(func.count()) \
            .where(ContestProblem.contest_id == contest_id) \
            .where(ContestProblem.problem_id == problem_id)
        with SqlSession() as db:
            return db.scalar(stmt) != 0

    @staticmethod
    def check_player_in_contest(contest_id: int, username: str):
        stmt = select(func.count()) \
            .where(ContestPlayer.c.Belong == contest_id) \
            .where(ContestPlayer.c.Username == username)
        with SqlSession() as db:
            return db.scalar(stmt) != 0

    @staticmethod
    def get_unfinished_exam_info_for_player(username: str, cur_time: int) -> Tuple[int, bool]:
        """
            return exam_id, is_exam_started
        """
        j = join(Contest, ContestPlayer, ContestPlayer.c.Belong == Contest.id)
        stmt = select(Contest.id, Contest.start_time) \
            .select_from(j) \
            .where(Contest.type == 2) \
            .where(cur_time <= Contest.end_time) \
            .where(ContestPlayer.c.Username == username) \
            .order_by(Contest.id.desc()) \
            .limit(1)
        with SqlSession() as db:
            data = db.execute(stmt).first()
        if data is not None:
            return data[0], (cur_time >= int(data[1]))
        return -1, False

    @staticmethod
    def delete_player_from_contest(contest_id: int, username: str):
        try:
            stmt = delete(ContestPlayer) \
                .where(ContestPlayer.c.Belong == contest_id) \
                .where(ContestPlayer.c.Username == username)
            with SqlSession.begin() as db:
                db.execute(stmt)
        except:
            sys.stderr.write("SQL Error in ContestManager: Delete_Player_From_Contest\n")

    @staticmethod
    def get_status(contest: Contest, time: Optional[int] = None) -> str:
        # Please ensure stability of these strings; they are more like enum values than UI strings.
        # They are compared with in jinja templates.
        if time is None:
            time = unix_nano()
        if time < contest.start_time:
            return 'Pending'
        elif time > contest.end_time:
            return 'Finished'
        else:
            return 'Going On'

    @staticmethod
    def list_contest(types: List[int], page: int, num_per_page: int,
                     keyword: Optional[str] = None, status: Optional[str] = None) -> Tuple[int, List[Contest]]:
        limit = num_per_page
        offset = (page - 1) * num_per_page
        stmt = select(Contest).where(Contest.type.in_(types))
        if keyword: # keyword is not None and len(keyword) > 0
            stmt = stmt.where(func.instr(Contest.name, keyword) > 0)
        if status:
            current_time = unix_nano()
            if status == 'Pending':
                stmt = stmt.where(Contest.start_time > current_time)
            elif status == 'Going On':
                stmt = stmt.where(Contest.start_time <= current_time) \
                    .where(Contest.end_time >= current_time)
            elif status == 'Finished':
                stmt = stmt.where(Contest.end_time < current_time)
        stmt_count = stmt.with_only_columns(func.count())
        stmt_data = stmt.order_by(Contest.id.desc()) \
            .limit(limit).offset(offset)
        with SqlSession(expire_on_commit=False) as db:
            count = db.scalar(stmt_count)
            this_page = db.scalars(stmt_data).all()
            return count, this_page

    @staticmethod
    def get_time(contest_id: int):
        stmt = select(Contest.start_time, Contest.end_time).where(Contest.id == contest_id)
        with SqlSession() as db:
            data = db.execute(stmt).first()
            return int(data[0]), int(data[1])

    @staticmethod
    def list_problem_for_contest(contest_id: int):
        stmt = select(ContestProblem.problem_id).where(ContestProblem.contest_id == contest_id)
        with SqlSession() as db:
            data = db.scalars(stmt).all()
            return data

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
        stmt = select(func.max(Contest.id))
        with SqlSession() as db:
            data = db.scalar(stmt)
            return int(data) if data is not None else 0

    @staticmethod
    def get_contest_type(contest_id: int) -> int:
        stmt = select(Contest.type).where(Contest.id == contest_id)
        with SqlSession() as db:
            data = db.scalar(stmt)
            return int(data) if data is not None else 0

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
                'realname': RealnameManager.Query_Realname(user.student_id),
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
                .where(JudgeRecord2.username.in_([x.username for x in players])) \
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
