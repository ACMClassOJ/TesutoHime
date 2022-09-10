from dataclasses import dataclass, field
from enum import Enum
from pathlib import PosixPath
from typing import List, Literal, Optional, Union

# scheduler -> runner

Url = str
FileUrl = Url

@dataclass
class CompileSourceCpp:
    main: FileUrl
    type: Literal['cpp'] = 'cpp'

@dataclass
class CompileSourceGit:
    url: Url
    type: Literal['git'] = 'git'

@dataclass
class CompileSourceVerilog:
    main: FileUrl
    type: Literal['verilog'] = 'verilog'


CompileSource = Union[
    CompileSourceCpp,
    CompileSourceGit,
    CompileSourceVerilog,
]


@dataclass
class Artifact:
    url: FileUrl
    type: Literal['artifact'] = 'artifact'

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
    type: Literal['compile'] = 'compile'


Input = Union[CompileTask, Artifact]


@dataclass
class RunArgs:
    type: Literal['elf', 'valgrind', 'verilog']
    limits: ResourceUsage
    infile: Optional[FileUrl]
    supplementary_files: List[FileUrl]


@dataclass
class CompareChecker:
    ignore_whitespace: bool
    answer: FileUrl
    type: Literal['compare'] = 'compare'

@dataclass
class DirectChecker:
    type: Literal['direct'] = 'direct'

@dataclass
class SpjChecker:
    format: Literal['checker', 'scorer']
    executable: Input
    answer: Optional[FileUrl]
    supplementary_files: List[FileUrl]
    limits: ResourceUsage
    type: Literal['spj'] = 'spj'

Checker = Union[CompareChecker, DirectChecker, SpjChecker]


@dataclass
class Testpoint:
    id: str
    dependent_on: Optional[str] # id
    input: Input
    run: Optional[RunArgs]
    check: Checker

@dataclass
class JudgeTask:
    testpoints: List[Testpoint]
    type: Literal['judge'] = 'judge'


Task = Union[CompileTask, JudgeTask]


# runner -> scheduler, runner internal state

CompileError = Literal['compile_error']
RunError = Literal[
    'runtime_error',
    'time_limit_exceeded',
    'memory_limit_exceeded',
    'disk_limit_exceeded',
    'memory_leak',
]
CheckError = Literal['wrong_answer']
Skipped = Literal['skipped']
Void = Literal['void']
Aborted = Literal['aborted']
Judging = Literal['judging']
Pending = Literal['pending']
MiscError = Literal[
    'system_error',
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
    RunError,
    Aborted,
    MiscError,
    Compiled,
]

@dataclass
class CompileResult:
    result: CompileResultType
    message: str
    type: Literal['compile_result'] = 'compile_result'

@dataclass
class RunResult:
    error: Optional[RunError]
    message: str
    resource_usage: Optional[ResourceUsage] = None
    code: Optional[int] = None # for runtime errors
    output_path: Optional[PosixPath] = None
    input_path: Optional[PosixPath] = None
    type: Literal['run_result'] = 'run_result'

@dataclass
class CompileLocalResult:
    result: CompileResult
    local_path: Optional[PosixPath]

    @staticmethod
    def from_run_failure(res: RunResult):
        return CompileLocalResult(
            CompileResult(res.error, res.message),
            None,
        )

    @staticmethod
    def from_file(file: PosixPath):
        return CompileLocalResult(
            CompileResult('compiled', 'Compiled'),
            file,
        )

CheckInput = Union[Input, RunResult]


@dataclass
class TestpointJudgeResult:
    id: Optional[str]
    result: ResultType
    message: str
    score: float = 0.0
    resource_usage: Optional[ResourceUsage] = None
    type: Literal['testpoint_judge_result'] = 'testpoint_judge_result'

@dataclass
class CheckResult:
    result: ResultType
    message: str
    score: float = 0.0


@dataclass
class JudgeResult:
    testpoints: List[TestpointJudgeResult]
    type: Literal['judge_result'] = 'judge_result'

Result = Union[CompileResult, JudgeResult]

class InvalidTaskException(Exception): pass

@dataclass
class StatusUpdateStarted: pass
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
    task: JudgeTask
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
    type: Literal['SELECT']
    title: str
    answer: str
    options: List


@dataclass
class JudgePlan:
    compile: Optional[CompileTaskPlan] = None
    judge: List[JudgeTaskPlan] = None
    score: List[TestpointGroup] = None
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