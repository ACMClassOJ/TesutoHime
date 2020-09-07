from enum import Enum
from Judger.Judger_Data import ProblemConfig

class ResultType(Enum):
        AC = 'Accepted'
        WA = 'Wrong Answer'
        RE = 'Runtime Error'
        TLE = 'Time Limit Exceeded'
        MLE = 'Memory Limit Exceeded'
        CE = 'Compile Error'
        MEMLEK = 'Memory Leak'
        SYSERR = 'System Error'
        SKIPED = 'Skiped'

class DetailResult:
        def __init__(self,
                ID: int,
                result: ResultType,
                score: int or float,
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
                Score, # int / float
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