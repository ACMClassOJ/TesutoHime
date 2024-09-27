from datetime import datetime
from enum import Enum, auto
from typing import Any, List, Optional, Set

from sqlalchemy import ARRAY as sa_ARRAY
from sqlalchemy import BigInteger, Computed
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing_extensions import Annotated, TypedDict


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

def ARRAY(*args, **kwargs):
    return MutableList.as_mutable(sa_ARRAY(*args, **kwargs))

class UseTimestamps:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class User(UseTimestamps, Base):
    id: Mapped[intpk]
    username: Mapped[str] = mapped_column(unique=True)
    username_lower: Mapped[str] = mapped_column(Computed('lower(username)'), unique=True)
    student_id: Mapped[str]
    friendly_name: Mapped[str]
    password: Mapped[str]
    privilege: Mapped[int]

    ignored_course_ids: Mapped[List[int]] = mapped_column(ARRAY(Integer), server_default='{}')
    data_license_agreed: Mapped[bool] = mapped_column(server_default=text('false'))

    external_contests: Mapped[Set['Contest']] = relationship(
        secondary='contest_player',
        passive_deletes=True,
        back_populates='external_players',
    )
    enrollments: Mapped[Set['Enrollment']] = relationship(back_populates='user')
    courses: AssociationProxy[Set['Course']] = association_proxy('enrollments', 'course')
    realname_references: Mapped[Set['RealnameReference']] = relationship(
        primaryjoin='foreign(User.student_id) == RealnameReference.student_id',
        uselist=True,
        viewonly=True,
    )
    access_tokens: Mapped[Set['AccessToken']] = relationship(back_populates='user')

user_fk = Annotated[int, mapped_column(ForeignKey(User.id), index=True)]

class CourseTag(UseTimestamps, Base):
    id: Mapped[intpk]
    name: Mapped[str]
    site_owner: Mapped[bool] = mapped_column(server_default=text('false'))

    courses: Mapped[Set['Course']] = relationship(back_populates='tag')

course_tag_fk = Annotated[int, mapped_column(ForeignKey(CourseTag.id), index=True)]

class Term(UseTimestamps, Base):
    id: Mapped[intpk]
    name: Mapped[str]
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]

    courses: Mapped[Set['Course']] = relationship(back_populates='term')

term_fk = Annotated[int, mapped_column(ForeignKey(Term.id), index=True)]

class Course(UseTimestamps, Base):
    id: Mapped[intpk]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(server_default='')

    tag_id: Mapped[Optional[course_tag_fk]]
    tag: Mapped[Optional[CourseTag]] = relationship(back_populates='courses')
    term_id: Mapped[Optional[term_fk]]
    term: Mapped[Optional[Term]] = relationship(back_populates='courses')

    groups: Mapped[List['Group']] = relationship(back_populates='course', order_by='Group.id')
    enrollments: Mapped[Set['Enrollment']] = relationship(back_populates='course')
    admin_enrollments: Mapped[Set['Enrollment']] = relationship(primaryjoin='and_(Course.id == Enrollment.course_id, Enrollment.admin)', viewonly=True)
    users: AssociationProxy[Set[User]] = association_proxy('enrollments', 'user')
    realname_references: Mapped[List['RealnameReference']] = relationship(back_populates='course', order_by='RealnameReference.id')
    problems: Mapped[Set['Problem']] = relationship(back_populates='course')
    contests: Mapped[List['Contest']] = relationship(back_populates='course', order_by='Contest.id')

course_fk = Annotated[int, mapped_column(ForeignKey(Course.id), index=True)]

class Enrollment(UseTimestamps, Base):
    __table_args__ = (
        Index('ix_enrollment_user_id_course_id', 'user_id', 'course_id', unique=True),
    )

    id: Mapped[intpk]
    user_id: Mapped[user_fk]
    user: Mapped[User] = relationship(back_populates='enrollments')
    course_id: Mapped[course_fk]
    course: Mapped[Course] = relationship(back_populates='enrollments')
    admin: Mapped[bool] = mapped_column(server_default=text('false'))

    realname_reference: Mapped[Optional['RealnameReference']] = relationship(
        secondary='user',
        primaryjoin='and_(Enrollment.course_id == RealnameReference.course_id, Enrollment.user_id == User.id)',
        secondaryjoin='User.student_id == RealnameReference.student_id',
        viewonly=True,
    )

class Group(UseTimestamps, Base):
    __table_args__ = (
        Index('ix_group_course_id_name', 'course_id', 'name', unique=True),
    )

    id: Mapped[intpk]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(server_default='')

    course_id: Mapped[course_fk]
    course: Mapped[Course] = relationship(back_populates='groups')

    realname_references: Mapped[Set['RealnameReference']] = relationship(
        secondary='group_realname_reference',
        passive_deletes=True,
        back_populates='groups',
    )

group_fk = Annotated[int, mapped_column(ForeignKey(Group.id, ondelete='CASCADE'), index=True)]

class RealnameReference(UseTimestamps, Base):
    __table_args__ = (
        Index('ix_realname_reference_student_id_course_id', 'student_id', 'course_id', unique=True),
    )

    id: Mapped[intpk]
    student_id: Mapped[str] = mapped_column(index=True)
    real_name: Mapped[str]
    course_id: Mapped[course_fk]
    course: Mapped[Course] = relationship(back_populates='realname_references')

    groups: Mapped[Set[Group]] = relationship(
        secondary='group_realname_reference',
        passive_deletes=True,
        back_populates='realname_references',
    )
    enrollments: Mapped[Set[Enrollment]] = relationship(
        secondary='user',
        primaryjoin='and_(Enrollment.course_id == RealnameReference.course_id, User.student_id == RealnameReference.student_id)',
        secondaryjoin='User.id == Enrollment.user_id',
        viewonly=True,
    )

realname_reference_fk = Annotated[int, mapped_column(ForeignKey(RealnameReference.id, ondelete='CASCADE'), index=True)]

class GroupRealnameReference(UseTimestamps, Base):
    __table_args__ = (
        Index('ix_group_realname_reference_group_id_realname_reference_id', 'group_id', 'realname_reference_id', unique=True),
    )

    id: Mapped[intpk]
    group_id: Mapped[group_fk]
    realname_reference_id: Mapped[realname_reference_fk]


class ProblemExample(TypedDict):
    name: Optional[str]
    input: Optional[str]
    output: Optional[str]
    description: Optional[str]

class Problem(UseTimestamps, Base):
    __table_args__ = (
        Index('release_time_id', 'release_time', 'id'),
    )

    id: Mapped[intpk]
    title: Mapped[str]
    course_id: Mapped[course_fk]
    course: Mapped[Course] = relationship(back_populates='problems')

    # problem description
    description: Mapped[Optional[str]]
    input: Mapped[Optional[str]]
    output: Mapped[Optional[str]]
    examples: Mapped[List[ProblemExample]] = mapped_column(ARRAY(JSONB), server_default='{}')
    example_input: Mapped[Optional[str]]
    example_output: Mapped[Optional[str]]
    data_range: Mapped[Optional[str]]
    limits: Mapped[Optional[Any]] = mapped_column(JSONB)

    release_time: Mapped[datetime]
    problem_type: Mapped[int] = mapped_column(server_default=text('0'))
    languages_accepted: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), server_default='{}')
    allow_public_submissions: Mapped[bool] = mapped_column(server_default=text('true'))

    contests: Mapped[Set['Contest']] = relationship(
        secondary='contest_problem',
        passive_deletes=True,
        back_populates='problems',
    )
    discussions: Mapped[Set['Discussion']] = relationship()
    privileges: Mapped[Set['ProblemPrivilege']] = relationship(back_populates='problem')

problem_fk = Annotated[int, mapped_column(ForeignKey(Problem.id), index=True)]


class ProblemPrivilegeType(Enum):
    readonly = auto()
    owner = auto()

class ProblemPrivilege(UseTimestamps, Base):
    id: Mapped[intpk]
    user_id: Mapped[user_fk]
    user: Mapped[User] = relationship()
    problem_id: Mapped[problem_fk]
    problem: Mapped[Problem] = relationship(back_populates='privileges')
    privilege: Mapped[ProblemPrivilegeType] = mapped_column(SqlEnum(ProblemPrivilegeType))
    comment: Mapped[str] = mapped_column(server_default='')


class CompletionCriteriaType(Enum):
    none = auto()
    simple = auto()
    python = auto()

class Contest(UseTimestamps, Base):
    id: Mapped[intpk]
    name: Mapped[str]
    description: Mapped[str] = mapped_column(server_default='')

    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    late_submission_deadline: Mapped[Optional[datetime]]
    type: Mapped[int] = mapped_column(index=True)
    ranked: Mapped[bool]
    rank_penalty: Mapped[bool]
    rank_partial_score: Mapped[bool]

    course_id: Mapped[course_fk]
    course: Mapped[Course] = relationship(back_populates='contests')
    group_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer))
    rank_all_users: Mapped[bool] = mapped_column(server_default=text('false'))

    completion_criteria_type: Mapped[CompletionCriteriaType] = mapped_column(SqlEnum(CompletionCriteriaType), server_default='none')
    completion_criteria: Mapped[Optional[str]]
    allowed_languages: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))

    external_players: Mapped[Set[User]] = relationship(
        secondary='contest_player',
        passive_deletes=True,
        back_populates='external_contests',
    )
    problems: Mapped[List[Problem]] = relationship(
        secondary='contest_problem',
        order_by='ContestProblem.id',
        passive_deletes=True,
        back_populates='contests',
    )

contest_fk = Annotated[int, mapped_column(ForeignKey(Contest.id, ondelete='CASCADE'), index=True)]


class ContestPlayer(UseTimestamps, Base):
    id: Mapped[intpk]
    contest_id: Mapped[contest_fk]
    user_id: Mapped[user_fk]

class ContestProblem(UseTimestamps, Base):
    id: Mapped[intpk]
    contest_id: Mapped[contest_fk]
    problem_id: Mapped[problem_fk]


class Discussion(UseTimestamps, Base):
    id: Mapped[intpk]
    problem_id: Mapped[problem_fk]
    user_id: Mapped[user_fk]
    user: Mapped[User] = relationship()
    data: Mapped[str]


class JudgeRecordV1(Base):
    __table_args__ = (
        Index('problem_id_time', 'problem_id', 'time'),
    )

    id: Mapped[intpk]
    code: Mapped[str]
    user_id: Mapped[user_fk]
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
    bad_problem = auto()
    unknown_error = auto()

    accepted = auto()


class JudgeRecordV2(UseTimestamps, Base):
    __table_args__ = (
        Index('problem_id_created_at', 'problem_id', 'created_at'),
    )

    id: Mapped[intpk]
    public: Mapped[bool]
    language: Mapped[str] = mapped_column(index=True)
    user_id: Mapped[user_fk]
    user: Mapped[User] = relationship()
    problem_id: Mapped[problem_fk]
    problem: Mapped[Problem] = relationship()

    status: Mapped[JudgeStatus] = mapped_column(SqlEnum(JudgeStatus), index=True)
    score: Mapped[bigint] = mapped_column(server_default=text('0'))
    message: Mapped[Optional[str]]
    details: Mapped[Optional[str]]  # actually JSON of ProblemJudgeResult
    time_msecs: Mapped[Optional[bigint]]
    memory_bytes: Mapped[Optional[bigint]]

class OauthApp(UseTimestamps, Base):
    id: Mapped[intpk]
    client_id: Mapped[str] = mapped_column(index=True)
    client_secret: Mapped[str]
    redirect_uri: Mapped[str]
    name: Mapped[str]
    provider: Mapped[str]
    scopes: Mapped[List[str]] = mapped_column(ARRAY(Text))

oauth_app_fk = Annotated[int, mapped_column(ForeignKey(OauthApp.id, ondelete='CASCADE'), index=True)]

class AccessToken(UseTimestamps, Base):
    id: Mapped[intpk]
    token: Mapped[str] = mapped_column(index=True)
    name: Mapped[Optional[str]]

    user_id: Mapped[user_fk]
    user: Mapped[User] = relationship(back_populates='access_tokens')
    scopes: Mapped[List[str]] = mapped_column(ARRAY(Text))

    app_id: Mapped[Optional[oauth_app_fk]]
    app: Mapped[Optional[OauthApp]] = relationship()

    expires_at: Mapped[datetime]
    revoked_at: Mapped[Optional[datetime]]
