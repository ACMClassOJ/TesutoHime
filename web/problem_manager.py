from datetime import datetime
from http.client import BAD_REQUEST
from typing import List, Optional

from flask import abort, g
from sqlalchemy import func, select
from typing_extensions import TypeGuard

from commons.models import ContestProblem, Course, JudgeRecordV2, Problem
from web.const import PrivilegeType, language_info, FAR_FUTURE_TIME
from web.user_manager import UserManager
from web.utils import db


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
