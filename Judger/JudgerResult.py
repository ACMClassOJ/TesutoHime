from enum import Enum
from Judger_Data import ProblemConfig

class ResultType(Enum):
        AC = 0
        WA = 1
        RE = 2
        TLE = 3
        MLE = 4
        CE = 5
        MEMLEK = 6
        SYSERR = 7

class JudgerResult:
        def __init__(self,
                Status : ResultType,
                Score, # int / float
                TimeUsed : int, # ms
                MemUsed : int, # Byte
                Details, # [[ID, result: ResultType, score, time(ms), memory(Byte), disk(KB, -1 when not used), message: str]]
                Config : ProblemConfig
        ):
                self.Status = Status
                self.Score = Score
                self.TimeUsed = TimeUsed
                self.MemUsed = MemUsed
                self.Details = Details
                self.Config = Config