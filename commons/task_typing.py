from dataclasses import dataclass, field
from enum import Enum
from pathlib import PosixPath
from typing import List, Optional, TypeVar, Union

from typing_extensions import Generic, Literal

# scheduler -> runner

Url = str
FileUrl = Url

@dataclass
class CompileSourceCpp:
    main: FileUrl

@dataclass
class CompileSourceGit:
    url: Url

@dataclass
class CompileSourceVerilog:
    main: FileUrl


CompileSource = Union[
    CompileSourceCpp,
    CompileSourceGit,
    CompileSourceVerilog,
]


@dataclass
class Artifact:
    url: FileUrl

@dataclass
class ResourceUsage:
    time_msecs: int
    memory_bytes: int
    file_count: int
    file_size_bytes: int

@dataclass
class CompileTask:
    source: CompileSource
    supplementary_files: List[FileUrl]
    artifact: Optional[Artifact]
    limits: ResourceUsage


Input = Union[CompileTask, Artifact]


@dataclass
class RunArgs:
    # the value 'elf' has special meaning when used in a judge plan:
    # if type='elf' and code language is Python, then the type will be changed
    # to 'python' at plan execution time.
    type: Literal['elf', 'valgrind', 'verilog', 'python']
    limits: ResourceUsage
    infile: Optional[FileUrl]
    supplementary_files: List[FileUrl]
    outfile: Optional[Artifact] = None


@dataclass
class CompareChecker:
    ignore_whitespace: bool
    answer: FileUrl

@dataclass
class DirectChecker: pass

@dataclass
class SpjChecker:
    format: Literal['checker', 'scorer']
    executable: Input
    answer: Optional[FileUrl]
    supplementary_files: List[FileUrl]
    limits: ResourceUsage

Checker = Union[CompareChecker, DirectChecker, SpjChecker]
InputPlan = Union[Input, 'UserCode', 'CompileTaskPlan']
_TestpointInput = TypeVar('_TestpointInput', Input, InputPlan)


@dataclass
class Testpoint(Generic[_TestpointInput]):
    id: str
    dependent_on: Optional[str] # id
    input: _TestpointInput      # program to run
    run: Optional[RunArgs]
    check: Checker

@dataclass
class JudgeTask(Generic[_TestpointInput]):
    testpoints: List[Testpoint[_TestpointInput]]


Task = TypeVar('Task', CompileTask, JudgeTask[Input])


# runner -> scheduler, runner internal state

CompileError = Literal['compile_error']
RunError = Literal[
    'runtime_error',
    'time_limit_exceeded',
    'memory_limit_exceeded',
    'disk_limit_exceeded',
    'memory_leak',
    'system_error',
]
CheckError = Literal['wrong_answer', 'bad_problem']
Skipped = Literal['skipped']
Void = Literal['void']
Aborted = Literal['aborted']
Judging = Literal['judging']
Pending = Literal['pending']
MiscError = Literal[
    'unknown_error',
]
Accepted = Literal['accepted']
ResultType = Union[
    CompileError,
    RunError,
    CheckError,
    Skipped,
    Void,
    Aborted,
    Judging,
    Pending,
    MiscError,
    Accepted,
]

Compiled = Literal['compiled']
CompileResultType = Union[
    CompileError,
    RunError,
    Aborted,
    MiscError,
    Compiled,
]

@dataclass
class CompileResult:
    result: CompileResultType
    message: str

@dataclass
class RunResult:
    error: Optional[Union[CompileError, RunError]]
    message: str
    resource_usage: Optional[ResourceUsage] = None
    code: Optional[int] = None # for runtime errors
    output_path: Optional[PosixPath] = None
    input_path: Optional[PosixPath] = None

@dataclass
class CompileLocalResult:
    result: CompileResult
    local_path: Optional[PosixPath]

    @staticmethod
    def from_run_failure(res: RunResult):
        if res.error is None: raise Exception
        return CompileLocalResult(
            CompileResult(res.error, res.message),
            None,
        )

    @staticmethod
    def from_file(file: PosixPath, message: str = ''):
        return CompileLocalResult(
            CompileResult('compiled', message),
            file,
        )

CheckInput = Union[Input, RunResult]


@dataclass
class TestpointJudgeResult:
    id: str
    result: ResultType
    message: str
    score: float = 0.0
    resource_usage: Optional[ResourceUsage] = None

@dataclass
class CheckResult:
    result: ResultType
    message: str
    score: float = 0.0


@dataclass
class JudgeResult:
    testpoints: List[TestpointJudgeResult]

Result = Union[CompileResult, JudgeResult]

class InvalidTaskException(Exception): pass

@dataclass
class StatusUpdateStarted:
    id: str
@dataclass
class StatusUpdateProgress:
    result: Result
@dataclass
class StatusUpdateDone:
    result: Result
@dataclass
class StatusUpdateError:
    message: str

StatusUpdate = Union[
    StatusUpdateStarted,
    StatusUpdateProgress,
    StatusUpdateDone,
    StatusUpdateError,
]


# scheduler internal state

class CodeLanguage(Enum):
    CPP = 'cpp'
    PYTHON = 'python'
    GIT = 'git'
    VERILOG = 'verilog'
    QUIZ = 'quiz'


@dataclass
class UserCode:
    filename: Optional[str] = None

@dataclass
class CompileTaskPlan:
    source: Union[CompileSource, UserCode]
    supplementary_files: List[Union[FileUrl, UserCode]]
    artifact: bool
    limits: ResourceUsage

@dataclass
class JudgeTaskPlan:
    task: JudgeTask[InputPlan]
    dependencies: List[int]
    dependents: List[int]


@dataclass
class TestpointGroup:
    id: str
    name: str
    testpoints: List[str]
    score: float


@dataclass
class QuizOption:
    value: str
    text: str

@dataclass
class QuizProblem:
    id: str
    type: Literal['SELECT', 'FILL']
    title: str
    answer: Optional[str] = None
    options: Optional[List[QuizOption]] = None


DEFAULT_GROUP = 'default'

@dataclass
class JudgePlan:
    group: str = DEFAULT_GROUP
    compile: Optional[CompileTaskPlan] = None
    judge: List[JudgeTaskPlan] = field(default_factory=lambda: [])
    score: List[TestpointGroup] = field(default_factory=lambda: [])
    quiz: Optional[List[QuizProblem]] = None


@dataclass
class GroupJudgeResult:
    id: str
    name: str
    result: ResultType
    testpoints: List[TestpointJudgeResult]
    score: float

@dataclass
class ProblemJudgeResult:
    result: ResultType
    message: Optional[str]
    score: float = 0.0
    resource_usage: Optional[ResourceUsage] = None
    groups: List[GroupJudgeResult] = field(default_factory=lambda: [])


@dataclass
class SourceLocation:
    bucket: str
    key: str
