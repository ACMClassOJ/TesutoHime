from datetime import datetime
from enum import Enum, auto
from typing import List, Optional

from sqlalchemy import ARRAY, BigInteger, Column, Computed
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Integer, Table, Text, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated


class Base(DeclarativeBase):
    type_annotation_map = {
        str: Text,
    }

    def __init_subclass__(cls) -> None:
        if '__tablename__' not in cls.__dict__:
            name = ''
            for c in cls.__name__:
                if c.isupper():
                    if name != '':
                        name += '_'
                name += c.lower()
            setattr(cls, '__tablename__', name)
        return super().__init_subclass__()

metadata = Base.metadata  # type: ignore

intpk = Annotated[int, mapped_column(primary_key=True)]
bigint = Annotated[int, mapped_column(BigInteger)]

class UseTimestamps:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class User(UseTimestamps, Base):
    # 'user' is a keyword in postgresql :(
    __tablename__ = 'account'

    id: Mapped[intpk]
    username: Mapped[str] = mapped_column(unique=True)
    username_lower: Mapped[str] = mapped_column(Computed('lower(username)'), unique=True)
    student_id: Mapped[str]
    friendly_name: Mapped[str]
    password: Mapped[str]
    privilege: Mapped[int]

    contests: Mapped[List['Contest']] = relationship(
        secondary='contest_player',
        passive_deletes=True,
        back_populates='players',
    )

user_fk = Annotated[str, mapped_column(ForeignKey(User.username), index=True)]


class Problem(UseTimestamps, Base):
    __table_args__ = (
        Index('release_time_id', 'release_time', 'id'),
    )

    id: Mapped[intpk]
    title: Mapped[str]

    # problem description
    description: Mapped[Optional[str]]
    input: Mapped[Optional[str]]
    output: Mapped[Optional[str]]
    example_input: Mapped[Optional[str]]
    example_output: Mapped[Optional[str]]
    data_range: Mapped[Optional[str]]
    limits: Mapped[Optional[str]]

    release_time: Mapped[datetime]
    problem_type: Mapped[int] = mapped_column(server_default=text('0'))
    languages_accepted: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))

    contests: Mapped[List['Contest']] = relationship(
        secondary='contest_problem',
        passive_deletes=True,
        back_populates='problems',
    )

problem_fk = Annotated[int, mapped_column(ForeignKey(Problem.id), index=True)]


class Contest(UseTimestamps, Base):
    id: Mapped[intpk]
    name: Mapped[str]
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    type: Mapped[int] = mapped_column(index=True)
    ranked: Mapped[bool]
    rank_penalty: Mapped[bool]
    rank_partial_score: Mapped[bool]

    players: Mapped[List[User]] = relationship(
        secondary='contest_player',
        passive_deletes=True,
        back_populates='contests',
    )
    problems: Mapped[List[Problem]] = relationship(
        secondary='contest_problem',
        passive_deletes=True,
        back_populates='contests',
    )


ContestPlayer = Table(
    'contest_player',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('contest_id', Integer, ForeignKey(Contest.id), index=True),
    Column('username', Text, ForeignKey(User.username), index=True),
    Index('contest_id_username', 'contest_id', 'username'),
)

ContestProblem = Table(
    'contest_problem',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('contest_id', Integer, ForeignKey(Contest.id), index=True),
    Column('problem_id', Integer, ForeignKey(Problem.id), index=True),
)


class Discussion(UseTimestamps, Base):
    id: Mapped[intpk]
    problem_id: Mapped[problem_fk]
    username: Mapped[user_fk]
    data: Mapped[str]

Problem.discussions = relationship(Discussion)


class JudgeRecordV1(Base):
    __table_args__ = (
        Index('problem_id_time', 'problem_id', 'time'),
    )

    id: Mapped[intpk]
    code: Mapped[str]
    username: Mapped[user_fk]
    user: Mapped[User] = relationship()
    problem_id: Mapped[problem_fk]
    problem: Mapped[Problem] = relationship()
    language: Mapped[int]
    status: Mapped[int] = mapped_column(index=True)
    score: Mapped[int] = mapped_column(server_default=text('-1'))
    time: Mapped[bigint]
    time_msecs: Mapped[int] = mapped_column(server_default=text('-1'))
    memory_kbytes: Mapped[int] = mapped_column(server_default=text('-1'))
    detail: Mapped[Optional[str]]
    public: Mapped[bool] = mapped_column(server_default=text('false'))


class JudgeServerV1(Base):
    id: Mapped[intpk]
    base_url: Mapped[str]
    secret_key: Mapped[str] = mapped_column(unique=True)
    last_seen: Mapped[bigint] = mapped_column(server_default=text('0'))
    busy: Mapped[bool] = mapped_column(server_default=text('false'))
    current_task: Mapped[int] = mapped_column(server_default=text('-1'))
    friendly_name: Mapped[str]
    detail: Mapped[str]


class RealnameReference(UseTimestamps, Base):
    id: Mapped[intpk]
    student_id: Mapped[str] = mapped_column(index=True)
    real_name: Mapped[str]


# New models for judger2 and scheduler2


class JudgeRunnerV2(UseTimestamps, Base):
    id: Mapped[intpk]
    name: Mapped[str]
    hardware: Mapped[str]
    provider: Mapped[str]
    visible: Mapped[bool] = mapped_column(server_default=text('true'))


class JudgeStatus(Enum):
    pending = auto()
    compiling = auto()
    judging = auto()
    void = auto()
    aborted = auto()

    compile_error = auto()
    runtime_error = auto()
    time_limit_exceeded = auto()
    memory_limit_exceeded = auto()
    disk_limit_exceeded = auto()
    memory_leak = auto()

    wrong_answer = auto()
    skipped = auto()
    system_error = auto()
    unknown_error = auto()

    accepted = auto()


class JudgeRecordV2(UseTimestamps, Base):
    __table_args__ = (
        Index('problem_id_created_at', 'problem_id', 'created_at'),
    )

    id: Mapped[intpk]
    public: Mapped[bool]
    language: Mapped[str] = mapped_column(index=True)
    username: Mapped[user_fk]
    user: Mapped[User] = relationship()
    problem_id: Mapped[problem_fk]
    problem: Mapped[Problem] = relationship()

    status: Mapped[JudgeStatus] = mapped_column(SqlEnum(JudgeStatus), index=True)
    score: Mapped[bigint] = mapped_column(server_default=text('0'))
    message: Mapped[Optional[str]]
    details: Mapped[Optional[str]]  # actually JSON of ProblemJudgeResult
    time_msecs: Mapped[Optional[bigint]]
    memory_bytes: Mapped[Optional[bigint]]
