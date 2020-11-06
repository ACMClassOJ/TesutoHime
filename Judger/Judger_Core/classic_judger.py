from Judger_Core import judger_interface as interface
import JudgerResult as jr
from Judger_Core import config as conf
import random
import os
import time
import subprocess as sp
import resource
from config import Performance_Rate



class ClassicJudger(interface.JudgerInterface):
    def __init__(self):
        self.chroot_path = '/tmp/chroot'
        self.workspace_path = '/work/'
        self.exe_path = '/exe/'
        self.output_file = '/work/output.txt'

    def JudgeInstance(self, sub_config: conf.TestPointConfig, return_dict):

        if not os.path.exists(self.chroot_path):
            os.mkdir(self.chroot_path)
        else:
            os.system('rm ' + self.exe_path + '*')

        child=None
        try:
            # user_id=str(random.randint(99000,99999))
            # group_id=str(random.randint(99000,99999))
            os.system('cp ' + sub_config.programPath + ' /exe')
            if sub_config.valgrindTestOn:
                command = 'valgrind --tool=memcheck --leak-check=full --error-exitcode=1 --verbose' + \
                ' /exe/' + sub_config.programPath.split('/')[-1]

                child = sp.Popen(command, shell=True)
                exitcode = child.wait()
                mem, running_time, self.output_file = 0, 0, ''
                if exitcode != 0: 
                    return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.MEMLEK, 0, 0, 0, 0,
                                        ''), self.output_file
                    return
            else:
                user_id = str(99942)
                group_id = str(99958)
                command = '/bin/nsjail -Mo --chroot /tmp/chroot --quiet --max_cpus 1 --rlimit_fsize 1024 -t ' + \
                        str(int(sub_config.timeLimit / 1000 * Performance_Rate * 1.2 + 1)) + \
                        ' --cgroup_mem_mount ' + str(sub_config.memoryLimit) + \
                        ' --user ' + user_id + ' --group ' + group_id + \
                        ' -R /lib64 -R /lib  -R /exe /exe/' + sub_config.programPath.split('/')[-1] + \
                        ' <' + sub_config.inputFile + ' >' + self.output_file + ' 2>/dev/null'

                running_time = -time.time()
                child = sp.Popen(command, shell=True)
                child.wait()
                mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024  # may work or not
                running_time += time.time()
            disk = 0  # Not implemented

            if running_time > sub_config.timeLimit / 1000 * Performance_Rate:
                return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.TLE, 0, running_time * 1000 / Performance_Rate, mem, 0,
                                       ''), self.output_file
                return

            if mem > sub_config.memoryLimit:
                return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.MLE, 0, running_time * 1000 / Performance_Rate, mem, 0,
                                       ''), self.output_file
                return

        except sp.TimeoutExpired as e:
            child.kill()
            return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.TLE, 0, sub_config.timeLimit * 1.2, mem, 0, ''), self.output_file
            return
        except sp.CalledProcessError as e:
            return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.RE, 0, 0, mem, 0, ''), self.output_file
            return
        except Exception as e:
            print('!!! Unknown error', e)
            raise e

        return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.UNKNOWN if child.returncode == 0 else jr.ResultType.RE, 0,
                            running_time * 1000 / Performance_Rate, mem, 0, ''), self.output_file
        return
