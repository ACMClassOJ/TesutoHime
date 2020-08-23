from Judger.Judger_Core import judger_interface as interface
from Judger.Judger_Core.judger_interface import ResultConst
from Judger.Judger_Core import config as conf
import os
import time
import subprocess as sp
import resource


class ClassicJudger(interface.JudgerInterface):
    def __init__(self, exec_path: str, executable_name: str):
        self.exec_path = exec_path
        self.run = self.exec_path + ('/' if self.exec_path[-1] != '/' else '') + executable_name

    @staticmethod
    def GetResult(stat: ResultConst, out, std, time, mem, disk,
                  SPJ: interface.SPJInterface) -> conf.JudgeTestPointResult:
        score = 0.0
        msg = ''
        if stat == ResultConst.UNSURE:
            score, msg = SPJ.Compare(out, std)
            stat = ResultConst.SUCCESS if score >= 1 else ResultConst.WA
        return conf.JudgeTestPointResult(str(stat), score, msg, time, mem, disk)

    def JudgeInstance(self, sub_config: conf.ProblemSubtaskConfig,
                      SPJ: interface.SPJInterface) -> conf.JudgeTestPointResult:
        running_time = -time.time()
        try:
            child = sp.run(executable=self.run, stdin=sub_config.inputFiles, stdout=sp.PIPE, cwd=self.exec_path,
                           timeout=sub_config.timeLimit, universal_newlines=True)
            running_time += time.time()
            stat = ResultConst.UNSURE if child.returncode == 0 else ResultConst.RE
            mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss  # may work or not
            if mem > sub_config.memoryLimit:
                stat = ResultConst.MEM
            disk = 0  # Not implemented
            return ClassicJudger.GetResult(stat, child.stdout, sub_config.outputFiles, running_time, mem, disk, SPJ)

        except sp.TimeoutExpired as e:
            return ClassicJudger.GetResult(ResultConst.TLE, None, None, sub_config.timeLimit, 0, 0, SPJ)
        except sp.CalledProcessError as e:
            return ClassicJudger.GetResult(ResultConst.RE, None, None, time.time() + running_time, 0, 0, SPJ)
