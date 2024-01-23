from dataclasses import dataclass, field
from enum import IntEnum, unique
from typing import List, Optional, Union

from typing_extensions import Literal

from commons.task_typing import DEFAULT_GROUP


@unique
class Spj(IntEnum):
    CLASSIC_COMPARE = 0
    CLASSIC_SPJ = 1
    HPP_DIRECT = 2
    HPP_COMPARE = 3
    HPP_SPJ = 4
    NONE_SPJ = 5


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
    CompileTimeLimit: Optional[int] = None
    SPJ: Spj = Spj.CLASSIC_COMPARE
    Scorer: Literal[0] = 0
    SupportedFiles: List[str] = field(default_factory=lambda: [])
    Verilog: bool = False
    Quiz: bool = False
    RunnerGroup: str = DEFAULT_GROUP
