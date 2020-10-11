from Judger.Judger_Core import judger_interface as interface
import Judger.JudgerResult as jr
from Judger.Judger_Core import config as conf
import random
import os
import time
import subprocess as sp
import resource


chroot_path='/tmp/chroot'
workspace_path='/work/'
output_file='/work/output.txt'
class ClassicJudger(interface.JudgerInterface):
    def __init__(self):
        pass

    def JudgeInstance(self, sub_config: conf.TestPointConfig,) -> (jr.DetailResult, str):

        if not os.path.exists(workspace_path):
            os.mkdir(chroot_path)

        running_time = -time.time()
        try:
            user_id=str(random.randint(99000,99999))
            group_id=str(random.randint(99000,99999))
            command = '/bin/nsjail -Mo --chroot /tmp/chroot --max_cpus 1 -t '+str(sub_config.timeLimit)+' --user '+user_id+' --group '+group_id+' -R /lib64 -R /lib  -R '+sub_config.programPath+' <'+sub_config.inputFile+' >'+output_file
            child=sp.Popen(command,shell=True)
            child.communicate() # wait until stop
            # child = sp.run(executable=self.run, stdin=sub_config.inputFiles, stdout=sp.PIPE, cwd=self.exec_path,
                        #    timeout=sub_config.timeLimit, universal_newlines=True)
            running_time += time.time()
            stat = jr.ResultType.UNKNOWN if child.returncode == 0 else jr.ResultType.RE
            mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss  # may work or not
            if mem > sub_config.memoryLimit:
                return jr.DetailResult(0,jr.ResultType.UNKNOWN,0,running_time,mem,0,''),output_file
            disk = 0  # Not implemented
            return jr.DetailResult(0,jr.ResultType.MEMLEK,0,running_time,mem,0,''),output_file

        except sp.TimeoutExpired as e:
            return jr.DetailResult(0,jr.ResultType.TLE,0,0,mem,0,''),output_file
        except sp.CalledProcessError as e:
            return jr.DetailResult(0,jr.ResultType.RE,0,0,mem,0,''),output_file
