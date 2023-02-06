from enum import Enum, auto

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Table, Text, text
from sqlalchemy.dialects.mysql import (BIGINT, INTEGER, MEDIUMTEXT, TINYINT,
                                       TINYTEXT)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()
metadata = Base.metadata


class User(Base):
    __tablename__ = 'User'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column('tempID', INTEGER(11), primary_key=True)
    username = Column('Username', String(20), unique=True)
    student_id = Column('Student_ID', BIGINT(20))
    friendly_name = Column('Friendly_Name', TINYTEXT)
    password = Column('Password', TINYTEXT)
    salt = Column('Salt', INTEGER(11))
    privilege = Column('Privilege', INTEGER(11))


class Problem(Base):
    __tablename__ = 'Problem'
    __table_args__ = (
        Index('Release_Time_ID', 'Release_Time', 'ID'),
        {'mysql_charset': 'utf8mb4'},
    )

    id = Column('ID', INTEGER(11), primary_key=True)
    title = Column('Title', Text)
    description = Column('Description', Text)
    input = Column('Input', Text)
    output = Column('Output', Text)
    example_input = Column('Example_Input', Text)
    example_output = Column('Example_Output', Text)
    data_range = Column('Data_Range', Text)
    release_time = Column('Release_Time', BIGINT(20), nullable=False)
    flag_count = Column('Flag_Count', INTEGER(11), server_default=text("0"))
    problem_type = Column('Problem_Type', INTEGER(11), nullable=False, server_default=text("0"))
    limits = Column('Limits', Text)


class Contest(Base):
    __tablename__ = 'Contest'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column('ID', INTEGER(11), primary_key=True)
    name = Column('Name', TINYTEXT)
    start_time = Column('Start_Time', BIGINT(20))
    end_time = Column('End_Time', BIGINT(20))
    type = Column('Type', INTEGER(11), index=True)


ContestPlayer = Table(
    'Contest_Player',
    Base.metadata,
    Column('tempID', INTEGER(11), primary_key=True),
    Column('Belong', INTEGER(11), ForeignKey(Contest.id)),
    Column('Username', String(20), ForeignKey(User.username)),
    Index('Belong_Username', 'Belong', 'Username'),
)

Contest.players = relationship(
    User,
    ContestPlayer,
    back_populates="contests",
)
User.contests = relationship(
    Contest,
    ContestPlayer,
    back_populates="players",
)


class ContestProblem(Base):
    __tablename__ = 'Contest_Problem'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column('tempID', INTEGER(11), primary_key=True)
    contest_id = Column('Belong', INTEGER(11), ForeignKey(Contest.id), index=True)
    problem_id = Column('Problem_ID', INTEGER(11), ForeignKey(Problem.id))


class Discuss(Base):
    __tablename__ = 'Discuss'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column('ID', INTEGER(11), primary_key=True)
    problem_id = Column('Problem_ID', INTEGER(11), ForeignKey(Problem.id))
    username = Column('Username', String(20), ForeignKey(User.username))
    data = Column('Data', Text)
    time = Column('Time', BIGINT(20))

Problem.discussions = relationship(Discuss)


class JudgeRecord(Base):
    __tablename__ = 'Judge'
    __table_args__ = (
        Index('Problem_ID_Time', 'Problem_ID', 'Time'),
        {'mysql_charset': 'utf8mb4'},
    )

    id = Column('ID', INTEGER(11), primary_key=True)
    code = Column('Code', MEDIUMTEXT)
    username = Column('User', String(20), ForeignKey(User.username), index=True)
    user = relationship(User)
    problem_id = Column('Problem_ID', INTEGER(11), ForeignKey(Problem.id))
    problem = relationship(Problem)
    language = Column('Language', INTEGER(11))
    status = Column('Status', INTEGER(11), index=True)
    score = Column('Score', INTEGER(11), server_default=text("-1"))
    time = Column('Time', BIGINT(20))
    time_msecs = Column('Time_Used', INTEGER(11), server_default=text("-1"))
    memory_kbytes = Column('Mem_Used', INTEGER(11), server_default=text("-1"))
    detail = Column('Detail', MEDIUMTEXT)
    public = Column('Share', TINYINT(1), server_default=text("0"))


class JudgeServer(Base):
    __tablename__ = 'Judge_Server'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column('ID', INTEGER(11), primary_key=True)
    base_url = Column('Address', TINYTEXT)
    secret_key = Column('Secret_Key', TINYTEXT, unique=True)
    last_seen = Column('Last_Seen_Time', BIGINT(20), server_default=text("0"))
    busy = Column('Busy', TINYINT(1), server_default=text("0"))
    current_task = Column('Current_Task', INTEGER(11), server_default=text("-1"))
    friendly_name = Column('Friendly_Name', TINYTEXT)
    detail = Column('Detail', TINYTEXT)


class RealnameReference(Base):
    __tablename__ = 'Realname_Reference'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column('ID', INTEGER(11), primary_key=True)
    student_id = Column('Student_ID', BIGINT(20), index=True)
    real_name = Column('Real_Name', TINYTEXT)


# New models for judger2 and scheduler2


class DatabaseVersion(Base):
    __tablename__ = 'version'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    # database version, used for upgrades.
    version = Column(Integer, primary_key=True)


class JudgeRunner2(Base):
    __tablename__ = 'judge_runners2'
    __table_args__ = {'mysql_charset': 'utf8mb4'}

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    hardware = Column(Text)
    provider = Column(Text)


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


class JudgeRecord2(Base):
    __tablename__ = 'judge_records2'
    __table_args__ = (
        Index('problem_id_created', 'problem_id', 'created'),
        {'mysql_charset': 'utf8mb4'},
    )

    id = Column(Integer, primary_key=True)
    public = Column(Boolean)
    language = Column(Text)
    created = Column(DateTime, server_default=text('NOW()'))
    username = Column(String(20), ForeignKey(User.username), index=True)
    user = relationship(User)
    problem_id = Column(INTEGER(11), ForeignKey(Problem.id))
    problem = relationship(Problem)

    status = Column(SqlEnum(JudgeStatus), index=True)
    score = Column(BIGINT, default=0)
    message = Column(MEDIUMTEXT)
    details = Column(MEDIUMTEXT) # actually JSON of ProblemJudgeResult
    time_msecs = Column(BIGINT)
    memory_bytes = Column(BIGINT)
