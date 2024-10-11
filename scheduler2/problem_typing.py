'''
Typing for config.json. Please run:

    python3 -m scripts.generate_config_schema

to update the corresponding JSON schema after modifying this file.
'''

from dataclasses import dataclass, field
from enum import IntEnum, unique
from typing import List, Optional, Union

from typing_extensions import Literal

from commons.task_typing import DEFAULT_GROUP


@unique
class SpjNumeric(IntEnum):
    CLASSIC_COMPARE = 0
    CLASSIC_SPJ = 1
    HPP_DIRECT = 2
    HPP_COMPARE = 3
    HPP_SPJ = 4
    NONE_SPJ = 5

@dataclass
class SpjProgram:
    Type: Literal['cpp', 'binary']
    Path: str

CompileType = Literal['skip', 'classic', 'hpp']
RunType = Literal['skip', 'classic', 'verilog', 'interactive']
CheckType = Literal['skip', 'compare', 'custom']

@dataclass
class CompileConfig:
    Type: CompileType

@dataclass
class RunConfig:
    Type: RunType
    # For interactive
    Interactor: Optional[SpjProgram] = None

@dataclass
class CheckConfig:
    Type: CheckType
    # For compare
    IgnoreInsignificantWhitespace: bool = True
    # For custom
    Checker: Optional[SpjProgram] = None

@dataclass
class SpjConfig:
    Compile: Union[CompileType, CompileConfig] = 'classic'
    Run: Union[RunType, RunConfig] = 'classic'
    Check: Union[CheckType, CheckConfig] = 'compare'

@dataclass
class SpjConfigDesugared:
    Compile: CompileConfig
    Run: RunConfig
    Check: CheckConfig

spj_config_from_numeric = {
    SpjNumeric.CLASSIC_COMPARE: SpjConfig(),
    SpjNumeric.CLASSIC_SPJ: SpjConfig(Check='custom'),
    SpjNumeric.HPP_DIRECT: SpjConfig(Compile='hpp', Check='skip'),
    SpjNumeric.HPP_COMPARE: SpjConfig(Compile='hpp'),
    SpjNumeric.HPP_SPJ: SpjConfig(Compile='hpp', Check='custom'),
    SpjNumeric.NONE_SPJ: SpjConfig(Compile='skip', Run='skip', Check='custom'),
}


@dataclass
class Testpoint:
    ID: int
    Dependency: Optional[int] = None
    TimeLimit: Optional[int] = None
    MemoryLimit: Optional[int] = None
    DiskLimit: Optional[int] = None
    FileNumberLimit: Optional[int] = None
    ValgrindTestOn: bool = False


@dataclass
class Group:
    GroupID: int
    GroupScore: Union[int, float]
    TestPoints: List[int]
    GroupName: Optional[str] = None

@dataclass
class ProblemConfig:
    Details: List[Testpoint]
    Groups: List[Group]
    SPJ: SpjConfigDesugared
    CompileTimeLimit: Optional[int] = None
    Scorer: Literal[0] = 0
    SupportedFiles: List[str] = field(default_factory=lambda: [])
    Verilog: bool = False
    Quiz: bool = False
    RunnerGroup: str = DEFAULT_GROUP
