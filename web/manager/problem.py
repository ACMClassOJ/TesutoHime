from http.client import BAD_REQUEST
from typing import List, Optional

import sqlalchemy as sa
from flask import abort, g
from sqlalchemy import func, select
from sqlalchemy.orm import load_only
from typing_extensions import TypeGuard

from commons.models import ContestProblem, Course, JudgeRecordV2, Problem
from web.const import FAR_FUTURE_TIME, PrivilegeType, language_info
from web.manager.contest import ContestManager
from web.manager.user import UserManager
from web.utils import SearchDescriptor, db


class ProblemManager:
    @classmethod
    def create_problem(cls, course: Course) -> Problem:
        problem_id = cls.get_max_id() + 1
        problem = Problem(
            id=problem_id,
            title='新建题目',
            release_time=FAR_FUTURE_TIME,
            course_id=course.id,
        )
        db.add(problem)
        db.flush()
        return problem

    @staticmethod
    def hide_problem(problem: Problem):
        problem.release_time = FAR_FUTURE_TIME

    @staticmethod
    def show_problem(problem: Problem):
        problem.release_time = g.time

    @staticmethod
    def get_problem(problem_id: int) -> Optional[Problem]:
        return db.get(Problem, problem_id)

    @staticmethod
    def languages_accepted(problem: Problem) -> List[str]:
        if problem.languages_accepted is not None:
            return problem.languages_accepted
        default_languages = []
        for k in language_info:
            if language_info[k].acceptable_by_default:
                default_languages.append(k)
        return default_languages

    @staticmethod
    def get_max_id() -> int:
        stmt = select(func.max(Problem.id)).where(Problem.id < 11000)
        data = db.scalar(stmt)
        return data if data is not None else 0

    @staticmethod
    def can_show(problem: Optional[Problem]) -> TypeGuard[Problem]:
        return problem is not None and \
            (problem.release_time <= g.time or \
                UserManager.get_problem_privilege(g.user, problem) >= PrivilegeType.readonly)

    @staticmethod
    def can_read(problem: Problem) -> bool:
        return UserManager.get_problem_privilege(g.user, problem) >= PrivilegeType.readonly

    @staticmethod
    def can_write(problem: Problem) -> bool:
        return UserManager.get_problem_privilege(g.user, problem) >= PrivilegeType.owner

    @staticmethod
    def delete_problem(problem: Problem):
        submission_count = db.scalar(select(func.count())
                                     .where(JudgeRecordV2.problem_id == problem.id))
        contest_count = db.scalar(select(func.count())
                                  .where(ContestProblem.problem_id == problem.id))
        assert submission_count is not None
        assert contest_count is not None
        if submission_count > 0 or contest_count > 0:
            abort(BAD_REQUEST)
        db.delete(problem)

    class ProblemSearch(SearchDescriptor):
        __model__ = Problem
        __order__ = 'asc'

        @staticmethod
        def __base_query__():
            query = select(Problem).options(load_only(Problem.id, Problem.title, Problem.problem_type))
            if not UserManager.has_site_owner_tag(g.user):
                readable_course_ids = UserManager.get_readable_course_ids(g.user)
                query = query.where(sa.or_(Problem.release_time <= g.time,
                                           Problem.course_id.in_(readable_course_ids)))
            return query

        @staticmethod
        def keyword(keyword: str):
            return sa.func.strpos(Problem.title, keyword) > 0

        @staticmethod
        def type(type: int):
            return Problem.problem_type == type

        @staticmethod
        def problemset_id(id: int):
            contest = ContestManager.get_contest(id)
            if contest is None: return False
            problem_ids = ContestManager.list_problem_for_contest(contest)
            return Problem.id.in_(problem_ids)
