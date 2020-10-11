import subprocess as sp
from abc import abstractmethod
from Judger.Judger_Core import config as conf
from Judger.JudgerResult import DetailResult

class SPJInterface:
    @abstractmethod
    def Compare(self, running_output, std_output) -> (float, str): pass


class JudgerInterface:

    @abstractmethod
    def JudgeInstance(self, testConfig: conf.TestPointConfig) -> (DetailResult, str): pass

