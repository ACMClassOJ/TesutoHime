from datetime import datetime

from commons.models import JudgeStatus, Problem, User


# An extended view of JudgeRecord2, for typing only
class RowJudgeStatus:
    id: int
    public: bool
    language: str
    created: datetime
    username: str
    user: User
    problem_id: int
    problem: Problem
    status: JudgeStatus
    score: int
    message: str
    details: str
    time_msecs: int
    memory_bytes: int

    real_name: str
    visible: bool
