from Judger.Judger_Core import judger_interface as interface
import Judger.JudgerResult as jr
from Judger.Judger_Core import config as conf
import random
import os
import time
import subprocess as sp
import resource
from Judger.config import Performance_Rate

chroot_path = '/tmp/chroot'
workspace_path = '/work/'
exe_path = '/exe/'
output_file = '/work/output.txt'


class ClassicJudger(interface.JudgerInterface):
    def __init__(self):
        pass

    def JudgeInstance(self, sub_config: conf.TestPointConfig, ) -> (jr.DetailResult, str):

        if not os.path.exists(chroot_path):
            os.mkdir(chroot_path)

        child=None
        try:
            # user_id=str(random.randint(99000,99999))
            # group_id=str(random.randint(99000,99999))
            user_id = str(99942)
            group_id = str(99958)
            os.system('cp ' + sub_config.programPath + ' /exe')
            command = '/bin/nsjail -Mo --chroot /tmp/chroot --quiet --max_cpus 1 --rlimit_fsize 1024 -t ' + \
                      str(int(sub_config.timeLimit / 1000 * Performance_Rate * 1.2 + 1)) + \
                      ' --cgroup_mem_mount ' + str(sub_config.memoryLimit) + \
                      ' --user ' + user_id + ' --group ' + group_id + \
                      ' -R /lib64 -R /lib  -R /exe /exe/' + sub_config.programPath.split('/')[-1] + \
                      ' <' + sub_config.inputFile + ' >' + output_file + ' 2>/dev/null'

            running_time = -time.time()
            child = sp.Popen(command, shell=True)
            child.wait()
            running_time += time.time()
            mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024  # may work or not
            disk = 0  # Not implemented

            if running_time > sub_config.timeLimit / 1000 * Performance_Rate:
                return jr.DetailResult(0, jr.ResultType.TLE, 0, running_time * 1000 / Performance_Rate, mem, 0,
                                       ''), output_file

            if mem > sub_config.memoryLimit:
                return jr.DetailResult(0, jr.ResultType.MLE, 0, running_time * 1000 / Performance_Rate, mem, 0,
                                       ''), output_file

            return jr.DetailResult(0, jr.ResultType.UNKNOWN if child.returncode == 0 else jr.ResultType.RE, 0,
                                   running_time * 1000 / Performance_Rate, mem, 0, ''), output_file

        except sp.TimeoutExpired as e:
            child.kill()
            return jr.DetailResult(0, jr.ResultType.TLE, 0, sub_config.timeLimit * 1.2, mem, 0, ''), output_file
        except sp.CalledProcessError as e:
            return jr.DetailResult(0, jr.ResultType.RE, 0, 0, mem, 0, ''), output_file
        except Exception as e:
            print('!!! Unknown error', e)
            raise e
