from datetime import datetime
from http.client import BAD_REQUEST
from typing import List, Optional
from typing_extensions import TypeGuard

from flask import abort, g
from sqlalchemy import delete, func, select, update

from commons.models import ContestProblem, JudgeRecordV2, Problem
from web.const import Privilege, language_info
from web.session_manager import SessionManager
from web.utils import db

FAR_FUTURE_TIME = datetime(9999, 12, 31, 8, 42, 42)


class ProblemManager:
    @staticmethod
    def add_problem() -> int:
        problem_id = ProblemManager.get_max_id() + 1
        problem = Problem(
            id=problem_id,
            release_time=FAR_FUTURE_TIME
        )
        db.add(problem)
        return problem_id

    @staticmethod
    def modify_problem_description(problem_id: int, description: str, problem_input: str, problem_output: str,
                                   example_input: str, example_output: str, data_range: str):
        stmt = update(Problem).where(Problem.id == problem_id) \
            .values(description=description,
                    input=problem_input,
                    output=problem_output,
                    example_input=example_input,
                    example_output=example_output,
                    data_range=data_range)
        db.execute(stmt)

    @staticmethod
    def modify_problem(problem_id: int, title: str, release_time: datetime, problem_type: int):
        stmt = update(Problem).where(Problem.id == problem_id) \
            .values(title=title,
                    release_time=release_time,
                    problem_type=problem_type)
        db.execute(stmt)

    @staticmethod
    def hide_problem(problem_id: int):
        stmt = update(Problem).where(Problem.id == problem_id) \
            .values(release_time=FAR_FUTURE_TIME)
        db.execute(stmt)

    @staticmethod
    def show_problem(problem_id: int):
        stmt = update(Problem).where(Problem.id == problem_id) \
            .values(release_time=g.time)
        db.execute(stmt)

    @staticmethod
    def get_problem(problem_id: int) -> Optional[Problem]:
        return db.get(Problem, problem_id)

    @staticmethod
    def modify_problem_limit(problem_id: int, limit: str):
        stmt = update(Problem) \
            .where(Problem.id == problem_id) \
            .values(limits=limit)
        db.execute(stmt)

    @staticmethod
    def get_title(problem_id: int) -> str:
        stmt = select(Problem.title).where(Problem.id == problem_id)
        data = db.scalar(stmt)
        return data if data is not None else ""

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
    def set_languages_accepted(problem_id: int, languages: Optional[List[str]]):
        stmt = update(Problem) \
            .values(languages_accepted=languages) \
            .where(Problem.id == problem_id)
        db.execute(stmt)

    @staticmethod
    def get_max_id() -> int:
        stmt = select(func.max(Problem.id)).where(Problem.id < 11000)
        data = db.scalar(stmt)
        return data if data is not None else 0

    @staticmethod
    def should_show(problem: Optional[Problem]) -> TypeGuard[Problem]:
        return problem is not None and \
            (problem.release_time <= g.time
             or SessionManager.get_privilege() >= Privilege.ADMIN)

    @staticmethod
    def delete_problem(problem_id: int):
        submission_count = db.scalar(select(func.count())
                                     .where(JudgeRecordV2.problem_id == problem_id))
        contest_count = db.scalar(select(func.count())
                                  .where(ContestProblem.c.problem_id == problem_id))
        assert submission_count is not None
        assert contest_count is not None
        if submission_count > 0 or contest_count > 0:
            abort(BAD_REQUEST)
        db.execute(delete(Problem).where(Problem.id == problem_id))
