from Judger.Judger_Core import judger_interface as interface
import Judger.JudgerResult as jr
from Judger.Judger_Core import config as conf
import random
import os
import time
import subprocess as sp
import resource
from Judger.config import Performance_Rate

chroot_path='/tmp/chroot'
workspace_path='/work/'
exe_path='/exe/'
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
            os.system('cp '+sub_config.programPath+' /exe')
            # command = '/bin/nsjail -Mo --chroot /tmp/chroot --quiet --max_cpus 1 -t '+str(sub_config.timeLimit/1000)+' --user '+user_id+' --group '+group_id+' -R /lib64 -R /lib  -R /exe /exe/'+sub_config.programPath.split('/')[-1]+' <'+sub_config.inputFile+' >'+output_file
            command = '/bin/nsjail -Mo --chroot /tmp/chroot --quiet --max_cpus 1 -t '+str(sub_config.timeLimit/1000 * Performance_Rate * 1.2)+' --cgroup_mem_mount '+str(sub_config.memoryLimit)+' --user '+user_id+' --group '+group_id+' -R /lib64 -R /lib  -R /exe /exe/'+sub_config.programPath.split('/')[-1]+' <'+sub_config.inputFile+' >'+output_file
            # print('aaaaaa:'+str(sub_config.timeLimit))

            child=sp.Popen(command,shell=True)
            # print('fu')
            # child.wait(timeout=sub_config.timeLimit/1000) # wait until stop
            # child.wait(timeout=1) # wait until stop
            child.wait()
            # print('ck')
            # child = sp.run(executable=self.run, stdin=sub_config.inputFiles, stdout=sp.PIPE, cwd=self.exec_path,
                        #    timeout=sub_config.timeLimit, universal_newlines=True)
            running_time += time.time()
            mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024  # may work or not
            disk = 0  # Not implemented

            if running_time > sub_config.timeLimit/1000 * Performance_Rate:
                return jr.DetailResult(0,jr.ResultType.TLE,0,running_time / Performance_Rate,mem,0,''),output_file

            if mem > sub_config.memoryLimit:
                return jr.DetailResult(0,jr.ResultType.MLE,0,running_time / Performance_Rate,mem,0,''),output_file

            return jr.DetailResult(0,jr.ResultType.UNKNOWN if child.returncode==0 else jr.ResultType.RE,0,running_time / Performance_Rate,mem,0,''),output_file

        except sp.TimeoutExpired as e:
            child.kill()
            return jr.DetailResult(0,jr.ResultType.TLE,0,sub_config.timeLimit/1000 * 1.2,mem,0,''),output_file
        except sp.CalledProcessError as e:
            return jr.DetailResult(0,jr.ResultType.RE,0,0,mem,0,''),output_file
        except Exception as e:
            print('!!! Unknown error',e)
            raise e