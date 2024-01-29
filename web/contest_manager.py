__all__ = ('ContestManager',)

from datetime import datetime
from functools import cmp_to_key
from typing import List, Optional, Sequence, Set, Tuple

from flask import g
from sqlalchemy import delete, func, insert, join, select, update
from sqlalchemy.orm import defer

from commons.models import (Contest, ContestPlayer, ContestProblem,
                            JudgeRecordV2, JudgeStatus, User)
from web.contest_cache import ContestCache
from web.realname_manager import RealnameManager
from web.utils import db, regularize_string


class ContestManager:
    @staticmethod
    def create_contest(id: int, name: str, start_time: datetime, end_time: datetime, contest_type: int,
                       ranked: bool, rank_penalty: bool, rank_partial_score: bool):
        contest = Contest(id=id,
                          name=name,
                          start_time=start_time,
                          end_time=end_time,
                          type=contest_type,
                          ranked=ranked,
                          rank_penalty=rank_penalty,
                          rank_partial_score=rank_partial_score)
        db.add(contest)

    @staticmethod
    def modify_contest(contest_id: int, new_name: str, new_start_time: datetime, new_end_time: datetime,
                       new_contest_type: int,
                       ranked: bool, rank_penalty: bool, rank_partial_score: bool):
        stmt = update(Contest).where(Contest.id == contest_id).values(
            name=new_name,
            start_time=new_start_time,
            end_time=new_end_time,
            type=new_contest_type,
            ranked=ranked,
            rank_penalty=rank_penalty,
            rank_partial_score=rank_partial_score
        )
        db.execute(stmt)

    @staticmethod
    def delete_contest(contest_id: int):
        db.execute(delete(Contest).where(Contest.id == contest_id))

    @staticmethod
    def add_problem_to_contest(contest_id: int, problem_id: int):
        db.add(ContestProblem(
            contest_id=contest_id,
            problem_id=problem_id,
        ))

    @staticmethod
    def delete_problem_from_contest(contest_id: int, problem_id: int):
        stmt = delete(ContestProblem) \
            .where(ContestProblem.contest_id == contest_id) \
            .where(ContestProblem.problem_id == problem_id)
        db.execute(stmt)

    @staticmethod
    def add_player_to_contest(contest_id: int, user: User):
        db.add(ContestPlayer(contest_id=contest_id, user_id=user.id))

    @staticmethod
    def check_problem_in_contest(contest_id: int, problem_id: int):
        stmt = select(func.count()) \
            .where(ContestProblem.contest_id == contest_id) \
            .where(ContestProblem.problem_id == problem_id)
        return db.scalar(stmt) != 0

    @staticmethod
    def get_unfinished_exam_info_for_player(user: User) -> Tuple[int, bool]:
        """
            return exam_id, is_exam_started
        """
        j = join(Contest, ContestPlayer, ContestPlayer.contest_id == Contest.id)
        stmt = select(Contest.id, Contest.start_time) \
            .select_from(j) \
            .where(Contest.type == 2) \
            .where(g.time <= Contest.end_time) \
            .where(ContestPlayer.user_id == user.id) \
            .order_by(Contest.id.desc()) \
            .limit(1)
        data = db.execute(stmt).first()
        if data is not None:
            return data[0], (g.time >= data[1])
        return -1, False

    @staticmethod
    def get_status(contest: Contest) -> str:
        # Please ensure stability of these strings; they are more like enum values than UI strings.
        # They are compared with in jinja templates.
        if g.time < contest.start_time:
            return 'Pending'
        elif g.time > contest.end_time:
            return 'Finished'
        else:
            return 'Going On'

    @staticmethod
    def list_contest(types: List[int], page: int, num_per_page: int,
                     keyword: Optional[str] = None,
                     status: Optional[str] = None) -> Tuple[int, Sequence[Contest]]:
        limit = num_per_page
        offset = (page - 1) * num_per_page
        stmt = select(Contest).where(Contest.type.in_(types))
        if keyword: # keyword is not None and len(keyword) > 0
            stmt = stmt.where(func.strpos(Contest.name, keyword) > 0)
        if status:
            current_time = g.time
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
        count = db.scalar(stmt_count)
        assert count is not None
        this_page = db.scalars(stmt_data).all()
        return count, this_page

    @staticmethod
    def list_problem_for_contest(contest_id: int) -> Sequence[int]:
        stmt = select(ContestProblem.problem_id).where(ContestProblem.contest_id == contest_id)
        data = db.scalars(stmt).all()
        return data

    @staticmethod
    def get_contest(contest_id: int) -> Optional[Contest]:
        return db.get(Contest, contest_id)

    @staticmethod
    def get_max_id() -> int:
        data = db.scalar(select(func.max(Contest.id)))
        return int(data) if data is not None else 0

    @staticmethod
    def get_scores(contest: Contest) -> List[dict]:
        start_time: datetime = contest.start_time
        end_time = contest.end_time
        problems = ContestManager.list_problem_for_contest(contest.id)
        players: Set[User] = contest.players

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
                'realname': RealnameManager.query_realname(user.student_id),
                'student_id': user.student_id,
                'username': user.username,
            } for user in players
        ]
        user_id_to_num = dict((user.id, i) for i, user in enumerate(players))
        problem_to_num = dict((problem, i) for i, problem in enumerate(problems))

        submits: List[JudgeRecordV2] = db \
            .query(JudgeRecordV2) \
            .options(defer(JudgeRecordV2.details), defer(JudgeRecordV2.message)) \
            .where(JudgeRecordV2.problem_id.in_(problems)) \
            .where(JudgeRecordV2.user_id.in_([x.id for x in players])) \
            .where(JudgeRecordV2.created_at >= start_time) \
            .where(JudgeRecordV2.created_at < end_time) \
            .all()
        for submit in submits:
            user_id = submit.user_id
            problem_id = submit.problem_id
            status = submit.status
            score = submit.score
            submit_time: datetime = submit.created_at

            if user_id not in user_id_to_num:
                continue

            rank = user_id_to_num[user_id]
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
                user_data['penalty'] += (int((submit_time - start_time).total_seconds()) + submit_count * 1200) // 60

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
        scores.sort(key=cmp_to_key(
            lambda x, y: y[key] - x[key] if x[key] != y[key] else x['penalty'] - y['penalty']))  # type: ignore
        for i, player in enumerate(scores):
            player['rank'] = i + 1
            if i > 0 and player[key] == scores[i - 1][key]:
                if contest.rank_penalty:
                    if player['penalty'] != scores[i - 1]['penalty']:
                        continue
                player['rank'] = scores[i - 1]['rank']

        return scores
