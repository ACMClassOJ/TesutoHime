__all__ = ('ContestManager',)

from datetime import datetime, timedelta
from functools import cmp_to_key
from typing import Dict, List, Optional, Sequence, Set, Tuple

from flask import g
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import defer

from commons.models import (Contest, ContestProblem, Course, Enrollment,
                            GroupRealnameReference, JudgeRecordV2, JudgeStatus,
                            RealnameReference, User)
from web.const import ContestType, PrivilegeType
from web.contest_cache import ContestCache
from web.user_manager import UserManager
from web.utils import db


class ContestManager:
    @staticmethod
    def create_contest(course: Course) -> Contest:
        end_time = datetime.now() if course.term is None else course.term.end_time
        contest = Contest(name='新建比赛',
                          start_time=datetime.now(),
                          end_time=end_time,
                          type=ContestType.CONTEST,
                          ranked=True,
                          rank_penalty=False,
                          rank_partial_score=True,
                          course_id=course.id)
        db.add(contest)
        db.flush()
        return contest

    @staticmethod
    def delete_contest(contest: Contest):
        db.delete(contest)
        db.flush()

    @staticmethod
    def delete_problem_from_contest(contest_id: int, problem_id: int):
        stmt = delete(ContestProblem) \
            .where(ContestProblem.contest_id == contest_id) \
            .where(ContestProblem.problem_id == problem_id)
        db.execute(stmt)

    @staticmethod
    def check_problem_in_contest(contest_id: int, problem_id: int):
        stmt = select(func.count()) \
            .where(ContestProblem.contest_id == contest_id) \
            .where(ContestProblem.problem_id == problem_id)
        return db.scalar(stmt) != 0


    @staticmethod
    def reason_cannot_join(contest: Contest) -> Optional[str]:
        if g.time > contest.end_time: return 'ended'
        if contest.type == ContestType.EXAM:
            exam_id, _ = ContestManager.get_unfinished_exam_info_for_player(g.user)
            if exam_id != -1: return 'in-exam'
        return None

    @classmethod
    def can_join(cls, contest: Contest) -> bool:
        return cls.reason_cannot_join(contest) is None

    @staticmethod
    def can_read(contest: Contest):
        return UserManager.get_contest_privilege(g.user, contest) >= PrivilegeType.readonly

    @staticmethod
    def can_write(contest: Contest):
        return UserManager.get_contest_privilege(g.user, contest) >= PrivilegeType.owner


    @classmethod
    def get_unfinished_exam_info_for_player(cls, user: User) -> Tuple[int, bool]:
        """
            return exam_id, is_exam_started
        """
        stmt = cls._get_implicit_contests_query(user) \
            .where(Contest.type == ContestType.EXAM) \
            .where(g.time <= Contest.end_time) \
            .order_by(Contest.id.desc())
        data = db.scalars(stmt).all()
        for contest in data:
            if not cls.can_read(contest):
                return contest.id, g.time >= contest.start_time
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
    def _get_implicit_players(contest: Contest) -> Sequence[User]:
        stmt = select(RealnameReference) \
            .where(RealnameReference.course_id == contest.course_id)
        if contest.group_ids is not None:
            stmt = stmt.where(select(GroupRealnameReference)
                              .where(GroupRealnameReference.realname_reference_id == RealnameReference.id)
                              .where(GroupRealnameReference.group_id.in_(contest.group_ids))
                              .exists())
        return [e.user for rr in db.scalars(stmt) for e in rr.enrollments if not e.admin]

    @classmethod
    def get_players(cls, contest: Contest) -> Set[User]:
        return set(contest.external_players).union(cls._get_implicit_players(contest))

    @staticmethod
    def _get_implicit_contests_query(user: User):
        # TODO: DB perf
        return select(Contest) \
            .join(Enrollment, Enrollment.course_id == Contest.course_id) \
            .where(Enrollment.user_id == user.id) \
            .where(~Enrollment.admin) \
            .join(RealnameReference, RealnameReference.course_id == Contest.course_id) \
            .where(RealnameReference.student_id == user.student_id) \
            .where(or_(Contest.group_ids == None,
                       select(GroupRealnameReference.id)
                       .where(GroupRealnameReference.realname_reference_id == RealnameReference.id)
                       .where(GroupRealnameReference.group_id == func.any(Contest.group_ids))
                       .exists()))

    @classmethod
    def _get_implicit_contests(cls, user: User) -> Sequence[Contest]:
        return list(db.scalars(cls._get_implicit_contests_query(user)))

    @classmethod
    def get_contests_for_user(cls, user: User) -> Set[Contest]:
        return set(user.external_contests).union(cls._get_implicit_contests(user))

    @staticmethod
    def get_contest(contest_id: int) -> Optional[Contest]:
        return db.get(Contest, contest_id)

    @classmethod
    def suggest_contests(cls, contests: Sequence[Contest]) -> Dict[str, List[dict]]:
        maxdelta = timedelta(3)
        suggested_contests: Dict[str, List[Contest]] = { 'in-progress': [], 'future': [], 'past': [] }
        for contest in contests:
            if contest.start_time <= g.time <= contest.end_time:
                suggested_contests['in-progress'].append(contest)
            elif contest.start_time - maxdelta <= g.time <= contest.start_time:
                suggested_contests['future'].append(contest)
            elif contest.end_time <= g.time <= contest.end_time + maxdelta:
                suggested_contests['past'].append(contest)

        suggested_contests['in-progress'].sort(key=lambda c: c.end_time)
        suggested_contests['future'].sort(key=lambda c: c.start_time)
        suggested_contests['past'].sort(key=lambda c: c.end_time, reverse=True)

        user_contests = cls.get_contests_for_user(g.user)
        suggestion: Dict[str, List[dict]] = { 'in-progress': [], 'future': [], 'past': [] }
        for k in suggested_contests:
            for contest in suggested_contests[k]:
                status = cls.get_status_for_card(contest, contest in user_contests)
                suggestion[k].append(status)

        return suggestion

    @classmethod
    def get_status_for_card(cls, contest: Contest, is_enrolled: bool) -> dict:
        completion_criteria = ''
        future = g.time < contest.start_time
        scores = cls.get_user_scores(contest, g.user)
        if contest.completion_criteria is not None:
            if contest.rank_partial_score:
                completion_criteria = f'需得到 {contest.completion_criteria} 分'
                if is_enrolled and not future and scores is not None:
                    completion_criteria += f'，已得到 {scores["score"]} 分'
            else:
                completion_criteria = f'需完成 {contest.completion_criteria} 题'
                if is_enrolled and not future and scores is not None:
                    completion_criteria += f'，已完成 {scores["ac_count"]} 题'

        retval = {
            'contest': contest,
            'status': '',
            'completion': completion_criteria,
            'enrolled': is_enrolled,
            'is-external': True if scores is None else scores['is_external'],
            'reason-cannot-join': cls.reason_cannot_join(contest),
        }
        if future:
            retval['status'] = 'future'
            return retval
        not_completed = False
        if contest.completion_criteria is not None and is_enrolled:
            if cls.user_has_completed_by_scores(contest, scores):
                retval['status'] = 'completed'
                return retval
            not_completed = True
        if contest.end_time < g.time:
            retval['status'] = 'past-not-completed' if not_completed else 'past'
            return retval
        maxdelta = min(
            (contest.end_time - contest.start_time) / 5,
            timedelta(2),
        )
        if contest.end_time - maxdelta <= g.time:
            retval['status'] = 'near-end'
        else:
            retval['status'] = 'in-progress'
        return retval

    @classmethod
    def get_scores(cls, contest: Contest) -> List[dict]:
        data = ContestCache.get(contest.id)
        if data is not None:
            return data

        start_time = contest.start_time
        end_time = contest.end_time
        problems = cls.list_problem_for_contest(contest.id)
        external_players = set(contest.external_players)
        implicit_players = set(cls._get_implicit_players(contest))
        players = external_players.union(implicit_players)

        data = [
            {
                'score': 0,
                'penalty': 0,
                'ac_count': 0,
                'friendly_name': user.friendly_name,
                'problems': [
                    {
                        'id': problem,
                        'score': 0,
                        'count': 0,
                        'pending_count': 0,
                        'accepted': False,
                    } for problem in problems
                ],
                'student_id': user.student_id,
                'username': user.username,
                'is_external': user not in implicit_players,
            } for user in players
        ]
        user_id_to_num = dict((user.id, i) for i, user in enumerate(players))
        problem_to_num = dict((problem, i) for i, problem in enumerate(problems))

        query = db \
            .query(JudgeRecordV2) \
            .options(defer(JudgeRecordV2.details), defer(JudgeRecordV2.message)) \
            .where(JudgeRecordV2.problem_id.in_(problems)) \
            .where(JudgeRecordV2.user_id.in_([x.id for x in players])) \
            .where(JudgeRecordV2.created_at >= start_time) \
            .where(JudgeRecordV2.created_at < end_time)
        if contest.allowed_languages is not None:
            query = query.where(JudgeRecordV2.language.in_(contest.allowed_languages))
        submits = query.all()
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
            problem = user_data['problems'][problem_index]  # type: ignore

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
                user_data['ac_count'] += 1  # type: ignore
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
    def user_has_completed_by_scores(contest: Contest, scores: dict) -> bool:
        if contest.completion_criteria is None:
            return False
        if contest.rank_partial_score:
            return scores['score'] >= contest.completion_criteria
        else:
            return scores['ac_count'] >= contest.completion_criteria

    @classmethod
    def get_user_scores(cls, contest: Contest, user: User) -> Optional[dict]:
        scores_all = cls.get_scores(contest)
        for scores in scores_all:
            if scores['username'] == user.username:
                return scores
        return None

    @classmethod
    def get_board_view(cls, contest: Contest) -> List[dict]:
        scores = cls.get_scores(contest)
        if not contest.ranked:
            implicit_players = filter(lambda x: not x['is_external'], scores)
            external_players = filter(lambda x: x['is_external'], scores)
            key_func = lambda x: x['friendly_name']
            return sorted(implicit_players, key=key_func) + sorted(external_players, key=key_func)

        key = 'score' if contest.rank_partial_score else 'ac_count'
        scores.sort(key=cmp_to_key(
            lambda x, y: y[key] - x[key] if x[key] != y[key] else x['penalty'] - y['penalty']))  # type: ignore
        current_rank = 1
        for i, player in enumerate(scores):
            player['rank'] = current_rank
            if not player['is_external']:
                current_rank += 1
            if i > 0 and player[key] == scores[i - 1][key]:
                if contest.rank_penalty:
                    if player['penalty'] != scores[i - 1]['penalty']:
                        continue
                player['rank'] = scores[i - 1]['rank']

        return scores
