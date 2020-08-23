import subprocess as sp
from abc import abstractmethod
from Judger.Judger_Core import config as conf
from enum import Enum


class ResultConst(Enum):
    # can change them to specify json
    UNSURE='MAY BUG'
    SUCCESS = 'Success'
    TLE = 'TLE'
    RE = 'RE'
    WA = 'WA'
    MEM='MEM'


class SPJInterface:
    @abstractmethod
    def Compare(self, running_output, std_output) -> (float, str): pass


class JudgerInterface:

    @abstractmethod
    def JudgeInstance(self, sub_config: conf.ProblemSubtaskConfig, SPJ: SPJInterface) -> conf.JudgeTestPointResult: pass
