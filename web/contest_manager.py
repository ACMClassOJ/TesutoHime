__all__ = ('ContestManager',)

from datetime import datetime, timedelta
from functools import cmp_to_key, wraps
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from flask import g
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import defer

from commons.models import (CompletionCriteriaType, Contest, ContestProblem, Course, Enrollment,
                            GroupRealnameReference, JudgeRecordV2, JudgeStatus,
                            RealnameReference, User)
from web.cache import Cache
from web.const import ContestType, PrivilegeType
from web.py_sanitize import PySanitizer
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
                          show_score=True,
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
    def get_implicit_players(contest: Contest) -> Sequence[User]:
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
        return set(contest.external_players).union(cls.get_implicit_players(contest))

    @staticmethod
    def check_implicit_membership(contest: Contest, user: User) -> bool:
        stmt = select(RealnameReference) \
            .where(RealnameReference.student_id == user.student_id) \
            .where(RealnameReference.course_id == contest.course_id) \
            .where(select(Enrollment)
                  .where(Enrollment.user_id == user.id)
                  .where(Enrollment.course_id == contest.course_id)
                  .exists())
        rr = db.scalar(stmt)
        if rr is None: return False
        if contest.group_ids is None: return True
        group_ids = [x.id for x in rr.groups]
        return any(x in contest.group_ids for x in group_ids)

    @staticmethod
    def _get_implicit_contests_query(user: User, include_admin = False,
                                     include_unofficial = False):
        # TODO: DB perf
        stmt = select(Contest) \
            .join(Enrollment, Enrollment.course_id == Contest.course_id) \
            .where(Enrollment.user_id == user.id)
        if not include_admin:
            stmt = stmt.where(~Enrollment.admin)
        if not include_unofficial:
            stmt = stmt \
                .join(RealnameReference, RealnameReference.course_id == Contest.course_id) \
                .where(RealnameReference.student_id == user.student_id) \
                .where(or_(Contest.group_ids == None,
                           select(GroupRealnameReference.id)
                           .where(GroupRealnameReference.realname_reference_id == RealnameReference.id)
                           .where(GroupRealnameReference.group_id == func.any(Contest.group_ids))
                           .exists()))
        return stmt

    @classmethod
    def get_implicit_contests(cls, user: User, include_admin = False,
                              include_unofficial = False) -> Sequence[Contest]:
        return db.scalars(cls._get_implicit_contests_query(user, include_admin, include_unofficial)).all()

    @classmethod
    def get_contests_for_user(cls, user: User, *,
                              include_admin = False,
                              include_unofficial = False) -> Set[Contest]:
        if 'user_contests' not in g:
            g.user_contests = {}
        cache_key = (user.id, include_admin, include_unofficial)
        if cache_key in g.user_contests:
            return g.user_contests[cache_key]
        contests = set(user.external_contests).union(cls.get_implicit_contests(user, include_admin, include_unofficial))
        g.user_contests[cache_key] = contests
        return contests

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

        user_contests = [x.id for x in cls.get_contests_for_user(g.user)]
        suggestion: Dict[str, List[dict]] = { 'in-progress': [], 'future': [], 'past': [] }
        for k in suggested_contests:
            for contest in suggested_contests[k]:
                status = cls.get_status_for_card(contest, contest.id in user_contests)
                suggestion[k].append(status)
            suggestion[k].sort(key=lambda s: s['enrolled'], reverse=True)

        return suggestion

    @classmethod
    def get_status_for_card(cls, contest: Contest, is_enrolled: bool) -> dict:
        future = g.time < contest.start_time
        if any(contest.id == x.id for x in cls.get_contests_for_user(g.user)):
            scores = cls.get_user_scores(contest, g.user)
        else:
            scores = None

        is_external = True if scores is None else scores['is_external']

        if contest.group_ids is None:
            course_member = not is_external
        else:
            stmt = select(Enrollment.id) \
                    .where(Enrollment.user_id == g.user.id) \
                    .where(Enrollment.course_id == contest.course_id) \
                    .where(Enrollment.admin == False) \
                    .where(select(RealnameReference)
                           .where(RealnameReference.student_id == g.user.student_id)
                           .where(RealnameReference.course_id == contest.course_id)
                           .exists())
            e = db.scalar(stmt)
            course_member = e is not None

        retval = {
            'contest': contest,
            'status': '',
            'completion': cls.get_completion_message(contest, scores, is_enrolled and not future),
            'enrolled': is_enrolled,
            'course-member': course_member,
            'is-external': is_external,
            'reason-cannot-join': cls.reason_cannot_join(contest),
        }
        if future:
            retval['status'] = 'future'
            return retval
        not_completed = False
        if contest.completion_criteria_type != CompletionCriteriaType.none and is_enrolled:
            if scores is not None and scores['completed']:
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

    @staticmethod
    def get_contest_submissions(contest: Contest, players: Iterable[User], *, no_details: bool = True) -> Sequence[JudgeRecordV2]:
        stmt = select(JudgeRecordV2)
        if no_details:
            stmt = stmt \
                .options(defer(JudgeRecordV2.details), defer(JudgeRecordV2.message))
        stmt = stmt \
            .where(JudgeRecordV2.problem_id.in_([x.id for x in contest.problems])) \
            .where(JudgeRecordV2.user_id.in_([x.id for x in players])) \
            .where(JudgeRecordV2.created_at >= contest.start_time) \
            .where(JudgeRecordV2.created_at < contest.end_time)
        if contest.allowed_languages is not None:
            stmt = stmt.where(JudgeRecordV2.language.in_(contest.allowed_languages))
        return db.scalars(stmt).all()

    _cache = Cache('contest', 14, json=True)
    _user_cache = Cache('contest-user', 14, json=True)

    @classmethod
    def get_scores(cls, contest: Contest, users: Optional[Set[User]] = None) -> List[dict]:
        if users is None:
            data = cls._cache.get(contest.id)
            if data is not None:
                return data

            external_players = set(contest.external_players)
            implicit_players = set(cls.get_implicit_players(contest))
            players = external_players.union(implicit_players)
        else:
            external_players = set()
            implicit_players = set()
            players = users
            for u in users:
                if u in contest.external_players:
                    external_players.add(u)
                if cls.check_implicit_membership(contest, u):
                    implicit_players.add(u)

        data = [
            {
                'score': 0,
                'penalty': 0,
                'ac_count': 0,
                'friendly_name': user.friendly_name,
                'problems': [
                    {
                        'id': problem.id,
                        'status': None,
                        'score': 0,
                        'count': 0,
                        'pending_count': 0,
                        'accepted': False,
                    } for problem in contest.problems
                ],
                'student_id': user.student_id,
                'id': user.id,
                'completed': False,
                'username': user.username,
                'is_external': user not in implicit_players,
            } for user in players
        ]
        user_id_to_user = dict((user.id, user) for user in players)
        user_id_to_num = dict((user.id, i) for i, user in enumerate(players))
        problem_to_num = dict((problem.id, i) for i, problem in enumerate(contest.problems))

        for submit in cls.get_contest_submissions(contest, players):
            user_id = submit.user_id
            problem_id = submit.problem_id
            status = submit.status
            score = submit.score
            submit_time = submit.created_at

            if user_id not in user_id_to_num:
                continue

            rank = user_id_to_num[user_id]
            problem_index = problem_to_num[problem_id]
            user_data = data[rank]
            problem = user_data['problems'][problem_index]  # type: ignore

            if problem['accepted']:
                continue
            max_score = problem['score']
            is_ac = status == JudgeStatus.accepted
            submit_count = problem['count']

            if int(score) > max_score:
                user_data['score'] -= max_score
                max_score = int(score)
                user_data['score'] += max_score
            if int(score) >= max_score:
                problem['status'] = submit.status.name

            if is_ac:
                problem['accepted'] = True
                problem['status'] = 'accepted'
                user_data['ac_count'] += 1  # type: ignore
                user_data['penalty'] += (int((submit_time - contest.start_time).total_seconds()) + submit_count * 1200) // 60

            if status in [JudgeStatus.pending, JudgeStatus.compiling, JudgeStatus.judging]:
                problem['pending_count'] += 1
            else:
                submit_count += 1

            problem['score'] = max_score
            problem['count'] = submit_count

        code = None
        if contest.completion_criteria_type == CompletionCriteriaType.python:
            if contest.completion_criteria is not None:
                code = cls._py_sanitizer.safe_compile(contest.completion_criteria)
        for player in data:
            user = user_id_to_user[player['id']]  # type: ignore
            player['completed'] = cls.user_has_completed_by_scores(contest, player, user, code)  # type: ignore

        if users is None:
            cls._cache.set(contest.id, data)

        return data

    @classmethod
    def get_user_scores(cls, contest: Contest, user: User) -> Optional[dict]:
        scores_all = cls._cache.get(contest.id)
        if scores_all is not None:
            for scores in scores_all:
                if scores['username'] == user.username:
                    return scores
            return None
        cached = cls._user_cache.hget(contest.id, user.id)
        if cached is not None:
            return cached
        scores = cls.get_scores(contest, users=set([user]))[0]
        cls._user_cache.hset(contest.id, user.id, scores)
        return scores

    @classmethod
    def flush_cache(cls, contest: Contest):
        cls._cache.flush(contest.id)
        cls._user_cache.flush(contest.id)

    _py_sanitizer = PySanitizer(['score', 'ac', 'count'], ['groups'])

    @classmethod
    def user_has_completed_by_scores(cls, contest: Contest,
                                     scores: Optional[dict],
                                     user: User,
                                     cached_code = None) -> Union[str, bool]:
        if scores is None:
            return False
        typ = contest.completion_criteria_type
        if typ == CompletionCriteriaType.none:
            return False
        elif typ == CompletionCriteriaType.simple:
            if contest.completion_criteria is None:
                return False
            try:
                crit = int(contest.completion_criteria)
            except ValueError as e:
                return str(e)
            if contest.rank_partial_score:
                return scores['score'] >= crit
            else:
                return scores['ac_count'] >= crit
        elif typ == CompletionCriteriaType.python:
            if contest.completion_criteria is None:
                return False
            def get_problem_score(index: int) -> dict:
                if type(index) != int:
                    raise TypeError(f'Problem index {index} should be int, not {type(index)}')
                if not (1 <= index <= len(scores['problems'])):
                    raise ValueError(f'Problem index {index} out of range')
                return scores['problems'][index - 1]

            def api(func):
                @wraps(func)
                def wrapped(*problems):
                    if len(problems) == 0:
                        return func(*scores['problems'])
                    return func(*(get_problem_score(x) for x in problems))
                return wrapped

            @api
            def score(*problems):
                return sum(x['score'] for x in problems)
            @api
            def count(*problems):
                return sum(1 if problem['accepted'] else 0 for problem in problems)
            @api
            def ac(*problems):
                return all(x['accepted'] for x in problems)

            enrollment = UserManager.get_enrollment(user, contest.course)
            if enrollment is None or enrollment.realname_reference is None:
                groups = []
            else:
                groups = [x.name for x in enrollment.realname_reference.groups]
            locals = { 'score': score, 'count': count, 'ac': ac, 'groups': groups }
            try:
                code = contest.completion_criteria if cached_code is None else cached_code
                retval = cls._py_sanitizer.safe_eval(code, locals)
                if type(retval) != bool:
                    raise TypeError(f'Return value must be a bool, not {repr(retval)}')
                return retval
            except Exception as e:
                return str(e)[:64]

    @classmethod
    def validate_completion_criteria(cls, contest: Contest,
                                     type: CompletionCriteriaType,
                                     value: Optional[str]) -> Optional[str]:
        if type == CompletionCriteriaType.none:
            pass
        elif type == CompletionCriteriaType.simple:
            if value is None or value == '':
                return '要求不能为空'
            try:
                crit = int(value)
            except ValueError as e:
                return str(e)
            if crit < 0:
                return '要求不能为负数'
            if not contest.rank_partial_score and crit > len(contest.problems):
                return '要求完成的题目数不能超过题目总数'
        elif type == CompletionCriteriaType.python:
            if value is None or value == '':
                return '要求不能为空'
            try:
                cls._py_sanitizer.safe_compile(value)
            except Exception as e:
                return str(e)
        return None

    @staticmethod
    def get_completion_message(contest: Contest, scores: Optional[dict],
                               show_current: bool) -> str:
        typ = contest.completion_criteria_type
        if typ == CompletionCriteriaType.simple:
            if contest.rank_partial_score:
                completion_criteria = f'需得到 {contest.completion_criteria} 分'
                if show_current and scores is not None:
                    completion_criteria += f'，已得到 {scores["score"]} 分'
            else:
                completion_criteria = f'需完成 {contest.completion_criteria} 题'
                if show_current and scores is not None:
                    completion_criteria += f'，已完成 {scores["ac_count"]} 题'
            return completion_criteria
        return ''

    @classmethod
    def get_board_view(cls, contest: Contest) -> List[dict]:
        scores = cls.get_scores(contest)
        if not contest.ranked:
            key_func = lambda x: x['friendly_name']
            if contest.rank_all_users:
                return sorted(scores, key=key_func)
            else:
                implicit_players = filter(lambda x: not x['is_external'], scores)
                external_players = filter(lambda x: x['is_external'], scores)
                return sorted(implicit_players, key=key_func) + sorted(external_players, key=key_func)

        key = 'score' if contest.rank_partial_score else 'ac_count'
        scores.sort(key=cmp_to_key(
            lambda x, y: y[key] - x[key] if x[key] != y[key] else x['penalty'] - y['penalty']))  # type: ignore
        current_rank = 1
        for i, player in enumerate(scores):
            player['rank'] = current_rank
            if not player['is_external'] or contest.rank_all_users:
                current_rank += 1
            if i > 0 and player[key] == scores[i - 1][key]:
                if contest.rank_penalty:
                    if player['penalty'] != scores[i - 1]['penalty']:
                        continue
                player['rank'] = scores[i - 1]['rank']

        return scores
