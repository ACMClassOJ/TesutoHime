from enum import Enum
from pathlib import PosixPath
from typing import Any, Self
from typing_extensions import Literal
from pydantic import ModelWrapValidatorHandler, model_validator
from pydantic.dataclasses import dataclass
from dataclasses import field

# scheduler -> runner

type Url = str
type FileUrl = Url


@dataclass
class DataclassBase:
    """
    The base class of all task related dataclasses, a compatibility layer to parsing from the old self-defined serialization format.
    It might be removed in the future.
    """

    @model_validator(mode="wrap")
    @classmethod
    def validate(cls, val: Any, handler: ModelWrapValidatorHandler[Self]) -> Self:
        match val:
            case {"type": str(t), "value": v}:
                if t != cls.__name__:
                    raise ValueError(f"Expected type {cls.__name__}, got {t}")
                return handler(v)
            case _:
                return handler(val)


@dataclass
class CompileSourceCpp(DataclassBase):
    main: FileUrl


@dataclass
class CompileSourceGit(DataclassBase):
    url: Url


@dataclass
class CompileSourceVerilog(DataclassBase):
    main: FileUrl


type CompileSource = CompileSourceCpp | CompileSourceGit | CompileSourceVerilog


@dataclass
class Artifact(DataclassBase):
    url: FileUrl


@dataclass
class ResourceUsage(DataclassBase):
    time_msecs: int
    memory_bytes: int
    file_count: int
    file_size_bytes: int


@dataclass
class CompileTask(DataclassBase):
    source: CompileSource
    supplementary_files: list[FileUrl]
    artifact: Artifact | None
    limits: ResourceUsage


type Input = CompileTask | Artifact


@dataclass
class InteractorOptions(DataclassBase):
    executable: Input
    limits: ResourceUsage
    supplementary_files: list[FileUrl]


type RunType = Literal["elf", "valgrind", "verilog", "python"]


@dataclass
class RunArgs(DataclassBase):
    # the value 'elf' has special meaning when used in a judge plan:
    # if type='elf' and code language is Python, then the type will be changed
    # to 'python' at plan execution time.
    type: RunType
    limits: ResourceUsage
    infile: FileUrl | None
    supplementary_files: list[FileUrl]
    outfile: Artifact | None = None
    interactor: InteractorOptions | None = None


@dataclass
class CompareChecker(DataclassBase):
    ignore_whitespace: bool
    answer: FileUrl


@dataclass
class DirectChecker(DataclassBase):
    pass


@dataclass
class SpjChecker(DataclassBase):
    format: Literal["checker", "scorer"]
    executable: Input
    answer: FileUrl | None
    supplementary_files: list[FileUrl]
    limits: ResourceUsage


type Checker = CompareChecker | DirectChecker | SpjChecker
type InputPlan = Input | UserCode | CompileTaskPlan


@dataclass
class Testpoint[T: (Input, InputPlan)](DataclassBase):
    id: str
    dependent_on: str | None  # id
    input: T  # program to run
    run: RunArgs | None
    check: Checker


@dataclass
class JudgeTask[T: (Input, InputPlan)](DataclassBase):
    testpoints: list[Testpoint[T]]


type TaskType = CompileTask | JudgeTask[Input]


# runner -> scheduler, runner internal state

type CompileError = Literal["compile_error"]
type RunError = Literal[
    "wrong_answer",
    "runtime_error",
    "time_limit_exceeded",
    "memory_limit_exceeded",
    "disk_limit_exceeded",
    "memory_leak",
    "system_error",
    "bad_problem",
]
type CheckError = Literal["wrong_answer", "bad_problem"]
type Skipped = Literal["skipped"]
type Void = Literal["void"]
type Aborted = Literal["aborted"]
type Judging = Literal["judging"]
type Pending = Literal["pending"]
type MiscError = Literal["unknown_error",]
type Accepted = Literal["accepted"]
type ResultType = (
    CompileError
    | RunError
    | CheckError
    | Skipped
    | Void
    | Aborted
    | Judging
    | Pending
    | MiscError
    | Accepted
)


type Compiled = Literal["compiled"]
type CompileResultType = CompileError | RunError | Aborted | MiscError | Compiled


@dataclass
class CompileResult(DataclassBase):
    result: CompileResultType
    message: str


@dataclass
class RunResult(DataclassBase):
    error: (CompileError | RunError) | None
    message: str
    resource_usage: ResourceUsage | None = None
    code: int | None = None  # for runtime errors
    output_path: PosixPath | None = None
    input_path: PosixPath | None = None


@dataclass
class CompileLocalResult(DataclassBase):
    result: CompileResult
    local_path: PosixPath | None

    @staticmethod
    def from_run_failure(res: RunResult) -> CompileLocalResult:
        if res.error is None:
            raise Exception
        return CompileLocalResult(
            CompileResult(res.error, res.message),
            None,
        )

    @staticmethod
    def from_file(file: PosixPath, message: str = "") -> CompileLocalResult:
        return CompileLocalResult(
            CompileResult("compiled", message),
            file,
        )


type CheckInput = Input | RunResult


@dataclass
class TestpointJudgeResult(DataclassBase):
    id: str
    result: ResultType
    message: str
    score: float = 0.0
    resource_usage: ResourceUsage | None = None


@dataclass
class CheckResult(DataclassBase):
    result: ResultType
    message: str
    score: float = 0.0


@dataclass
class JudgeResult(DataclassBase):
    testpoints: list[TestpointJudgeResult | None]


type Result = CompileResult | JudgeResult


class InvalidTaskException(Exception):
    pass


@dataclass
class StatusUpdateStarted(DataclassBase):
    id: str


@dataclass
class StatusUpdateProgress(DataclassBase):
    result: Result


@dataclass
class StatusUpdateDone(DataclassBase):
    result: Result


@dataclass
class StatusUpdateError(DataclassBase):
    message: str


type StatusUpdate = StatusUpdateStarted | StatusUpdateProgress | StatusUpdateDone | StatusUpdateError


# scheduler internal state


class CodeLanguage(Enum):
    CPP = "cpp"
    PYTHON = "python"
    GIT = "git"
    VERILOG = "verilog"
    QUIZ = "quiz"


@dataclass
class UserCode(DataclassBase):
    filename: str | None = None


@dataclass
class CompileTaskPlan(DataclassBase):
    source: CompileSource | UserCode
    supplementary_files: list[FileUrl | UserCode]
    artifact: bool
    limits: ResourceUsage


@dataclass
class JudgeTaskPlan(DataclassBase):
    task: JudgeTask[InputPlan]
    dependencies: list[int]
    dependents: list[int]


@dataclass
class TestpointGroup(DataclassBase):
    id: str
    name: str
    testpoints: list[str]
    score: float


@dataclass
class QuizOption(DataclassBase):
    value: str
    text: str


@dataclass
class QuizProblem(DataclassBase):
    id: str
    type: Literal["SELECT", "FILL"]
    title: str
    answer: str | None = None
    options: list[QuizOption] | None = None


DEFAULT_GROUP = "default"


@dataclass
class JudgePlan(DataclassBase):
    group: str = DEFAULT_GROUP
    compile: CompileTaskPlan | None = None
    judge: list[JudgeTaskPlan] = field(default_factory=lambda: [])
    score: list[TestpointGroup] = field(default_factory=lambda: [])
    quiz: list[QuizProblem] | None = None


# Please sync changes to web/static/api/api.yml
@dataclass
class TestpointSummary(DataclassBase):
    id: str
    limits: ResourceUsage | None


@dataclass
class SubtaskSummary(DataclassBase):
    id: str
    name: str
    testpoints: list[TestpointSummary]
    score: float


@dataclass
class JudgePlanSummary(DataclassBase):
    subtasks: list[SubtaskSummary]


@dataclass
class GroupJudgeResult(DataclassBase):
    id: str
    name: str
    result: ResultType
    testpoints: list[TestpointJudgeResult]
    score: float


@dataclass
class ProblemJudgeResult(DataclassBase):
    result: ResultType
    message: str | None
    score: float = 0.0
    resource_usage: ResourceUsage | None = None
    groups: list[GroupJudgeResult] = field(default_factory=lambda: [])


@dataclass
class SourceLocation(DataclassBase):
    bucket: str
    key: str
