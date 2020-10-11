from Judger.Judger_Core import judger_interface as interface
from Judger.Judger_Core.judger_interface import ResultConst
from Judger.Judger_Core import config as conf
from Judger.Judger_Core import classic_interaction as inter
from Judger import JudgerResult as jr
import random
import os
import time
import subprocess as sp
import resource


chroot_path='/tmp/chroot'
workspace_path='/work/'
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

    def JudgeInstance(self, sub_config: conf.TestPointConfig,) -> jr.DetailResult:
        running_time = -time.time()
        try:
            inter.create_environment()
            user_id=str(random.randint(99000,99999))
            group_id=str(random.randint(99000,99999))
            command = '/testdata/nsjail -Mo --chroot /tmp/chroot --max_cpus 1 -t '+sub_config.timeLimit+' --user '+user_id+' --group '+group_id+' -R /lib64 -R /lib  -R '+executable_path+' '+exec_name+' <'+input_path+' >'+output_path
            child=sp.Popen(command,shell=True)
            child.communicate() # wait until stop
            # child = sp.run(executable=self.run, stdin=sub_config.inputFiles, stdout=sp.PIPE, cwd=self.exec_path,
                        #    timeout=sub_config.timeLimit, universal_newlines=True)
            running_time += time.time()
            stat = ResultConst.UNSURE if child.returncode == 0 else ResultConst.RE
            mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss  # may work or not
            if mem > sub_config.memoryLimit:
                return jr.DetailResult(0,jr.UNKNOWN,0,running_time,mem,0,'')
            disk = 0  # Not implemented
            return jr.DetailResult(0,jr.MEMLEK,0,running_time,mem,0,'')

        except sp.TimeoutExpired as e:
            return jr.DetailResult(0,jr.TLE,0,0,mem,0,'')
        except sp.CalledProcessError as e:
            return jr.DetailResult(0,jr.RE,0,0,mem,0,'')
