from dataclasses import dataclass
from pathlib import PosixPath
from typing import List, Literal, Optional, Union


# scheduler -> runner

Url = str

@dataclass
class CompileSourceCpp:
    main: Url
    type: Literal['cpp'] = 'cpp'

@dataclass
class CompileSourceGit:
    url: Url
    type: Literal['git'] = 'git'

@dataclass
class CompileSourceVerilog:
    main: Url
    type: Literal['verilog'] = 'verilog'


CompileSource = Union[
    CompileSourceCpp,
    CompileSourceGit,
    CompileSourceVerilog,
]


@dataclass
class Artifact:
    url: Url
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
    supplementary_files: List[Url]
    artifact: Optional[Artifact]
    limits: ResourceUsage
    type: Literal['compile'] = 'compile'


Input = Union[CompileTask, Artifact]


@dataclass
class RunArgs:
    type: Literal['elf', 'valgrind', 'verilog']
    limits: ResourceUsage
    infile: Optional[Url]
    supplementary_files: List[Url]


@dataclass
class CompareChecker:
    ignore_whitespace: bool
    answer: Url
    type: Literal['compare'] = 'compare'

@dataclass
class DirectChecker:
    type: Literal['direct'] = 'direct'

@dataclass
class SpjChecker:
    format: Literal['checker', 'scorer']
    executable: Input
    answer: Optional[Url]
    supplementary_files: List[Url]
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
Cancelled = Literal['cancelled']
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
    Cancelled,
    MiscError,
    Accepted,
]

Compiled = Literal['compiled']
CompileResultType = Union[
    RunError,
    Cancelled,
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
    def from_run_failure (res: RunResult):
        return CompileLocalResult(
            CompileResult(res.error, res.message),
            None,
        )

    @staticmethod
    def from_file (file: PosixPath):
        return CompileLocalResult(
            CompileResult('compiled', 'Compiled'),
            file,
        )

CheckInput = Union[Input, RunResult]


@dataclass
class TestpointJudgeResult:
    testpoint_id: Optional[str]
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

class InvalidTaskException (Exception): pass


# scheduler internal state

@dataclass
class UserCode:
    filename: Optional[str] = None

@dataclass
class CompileTaskPlan:
    source: Union[CompileSource, UserCode]
    supplementary_files: List[Union[Url, UserCode]]
    artifact: bool
    limits: ResourceUsage

@dataclass
class JudgeTaskPlan:
    task: JudgeTask
    dependencies: List[int]
    dependents: List[int]


@dataclass
class TestpointGroup:
    name: str
    testpoints: List[str]
    score: float


@dataclass
class JudgePlan:
    compile: Optional[CompileTask] = None
    judge: List[JudgeTaskPlan] = None
    score: List[TestpointGroup] = None

