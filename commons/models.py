from enum import Enum, auto

from sqlalchemy import BigInteger, Boolean, Column, Computed, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Integer, Table, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


class GenerateName:
    def __init_subclass__(cls) -> None:
        if '__tablename__' not in cls.__dict__:
            name = ''
            for c in cls.__name__:
                if c.isupper():
                    if name != '':
                        name += '_'
                name += c.lower()
            cls.__tablename__ = name
        return super().__init_subclass__()

Base = declarative_base(cls=GenerateName)
metadata = Base.metadata


class User(Base):
    # 'user' is a keyword in postgresql :(
    __tablename__ = 'account'

    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True)
    username_lower = Column(Text, Computed('lower(username)'), unique=True)
    student_id = Column(Text)
    friendly_name = Column(Text)
    password = Column(Text)
    privilege = Column(Integer)


class Problem(Base):
    __table_args__ = (
        Index('release_time_id', 'release_time', 'id'),
    )

    id = Column(Integer, primary_key=True)
    title = Column(Text)

    # problem description
    description = Column(Text)
    input = Column(Text)
    output = Column(Text)
    example_input = Column(Text)
    example_output = Column(Text)
    data_range = Column(Text)

    release_time = Column(DateTime, nullable=False)
    problem_type = Column(Integer, nullable=False, server_default=text('0'))
    limits = Column(Text)


class Contest(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    type = Column(Integer, index=True)
    ranked = Column(Boolean, nullable=False)
    rank_penalty = Column(Boolean, nullable=False)
    rank_partial_score = Column(Boolean, nullable=False)


ContestPlayer = Table(
    'contest_player',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('contest_id', Integer, ForeignKey(Contest.id)),
    Column('username', Text, ForeignKey(User.username)),
    Index('contest_id_username', 'contest_id', 'username'),
)

Contest.players = relationship(
    User,
    ContestPlayer,
    back_populates='contests',
)
User.contests = relationship(
    Contest,
    ContestPlayer,
    back_populates='players',
)


class ContestProblem(Base):
    id = Column(Integer, primary_key=True)
    contest_id = Column(Integer, ForeignKey(Contest.id), index=True)
    problem_id = Column(Integer, ForeignKey(Problem.id), index=True)


class Discussion(Base):
    id = Column(Integer, primary_key=True)
    problem_id = Column(Integer, ForeignKey(Problem.id))
    username = Column(Text, ForeignKey(User.username))
    data = Column(Text)
    time = Column(DateTime)

Problem.discussions = relationship(Discussion)


class JudgeRecordV1(Base):
    __table_args__ = (
        Index('problem_id_time', 'problem_id', 'time'),
    )

    id = Column(Integer, primary_key=True)
    code = Column(Text)
    username = Column(Text, ForeignKey(User.username), index=True)
    user = relationship(User)
    problem_id = Column(Integer, ForeignKey(Problem.id))
    problem = relationship(Problem)
    language = Column(Integer)
    status = Column(Integer, index=True)
    score = Column(Integer, server_default=text('-1'))
    time = Column(BigInteger)
    time_msecs = Column(Integer, server_default=text('-1'))
    memory_kbytes = Column(Integer, server_default=text('-1'))
    detail = Column(Text)
    public = Column(Boolean, server_default=text('false'))


class JudgeServerV1(Base):
    id = Column(Integer, primary_key=True)
    base_url = Column(Text)
    secret_key = Column(Text, unique=True)
    last_seen = Column(BigInteger, server_default=text('0'))
    busy = Column(Boolean, server_default=text('false'))
    current_task = Column(Integer, server_default=text('-1'))
    friendly_name = Column(Text)
    detail = Column(Text)


class RealnameReference(Base):
    id = Column(Integer, primary_key=True)
    student_id = Column(Text, index=True)
    real_name = Column(Text)


# New models for judger2 and scheduler2


class JudgeRunnerV2(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    hardware = Column(Text)
    provider = Column(Text)
    visible = Column(Boolean, server_default=text('true'))


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


class JudgeRecordV2(Base):
    __table_args__ = (
        Index('problem_id_created', 'problem_id', 'created'),
    )

    id = Column(Integer, primary_key=True)
    public = Column(Boolean)
    language = Column(Text, index=True)
    created = Column(DateTime, server_default=text('NOW()'))
    username = Column(Text, ForeignKey(User.username), index=True)
    user = relationship(User)
    problem_id = Column(Integer, ForeignKey(Problem.id))
    problem = relationship(Problem)

    status = Column(SqlEnum(JudgeStatus), index=True)
    score = Column(BigInteger, default=0)
    message = Column(Text)
    details = Column(Text) # actually JSON of ProblemJudgeResult
    time_msecs = Column(BigInteger)
    memory_bytes = Column(BigInteger)
