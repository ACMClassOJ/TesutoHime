from enum import Enum
from Judger.Judger_Data import ProblemConfig

class ResultType(Enum):
        AC = 2
        WA = 3
        CE = 4
        RE = 5
        TLE = 6
        MLE = 7
        MEMLEK = 8
        SYSERR = 9
        SKIPPED = 10
        UNKNOWN = 11

class DetailResult:
        def __init__(self,
                ID: int,
                result: ResultType,
                score: int,
                time: int,
                memory: int,
                disk: int,
                message: str
        ):
                self.ID = ID
                self.result = result
                self.score = score
                self.time = time
                self.memory = memory
                self.disk = disk
                self.message = message

class JudgerResult:
        def __init__(self,
                Status : ResultType,
                Score : int,
                TimeUsed : int, # ms
                MemUsed : int, # Byte
                Details : list, # [Detail]
                Config : ProblemConfig
        ):
                self.Status = Status
                self.Score = Score
                self.TimeUsed = TimeUsed
                self.MemUsed = MemUsed
                self.Details = Details
                self.Config = Config