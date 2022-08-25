from dataclasses import dataclass, field
from enum import IntEnum, unique
from typing import List, Literal, Optional, Union


@unique
class Spj (IntEnum):
    CLASSIC_CLASSIC = 0
    CLASSIC_CHECKER = 1
    HPP_DIRECT = 2
    HPP_CLASSIC = 3
    HPP_CHECKER = 4
    NONE_CHECKER = 5


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
    SPJ: Spj = 0
    Scorer: Literal[0] = 0
    SupportedFiles: List[str] = field(default=lambda: [])
    Verilog: bool = False
