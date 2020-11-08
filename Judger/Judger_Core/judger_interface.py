import subprocess as sp
from abc import abstractmethod
from Judger_Core import config as conf
from JudgerResult import DetailResult

class SPJInterface:
    @abstractmethod
    def Compare(self, running_output, std_output) -> (float, str): pass


class JudgerInterface:

    @abstractmethod
    def JudgeInstance(self, testConfig: conf.TestPointConfig, return_dict): pass

