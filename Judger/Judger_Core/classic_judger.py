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
        if not os.path.exists(self.exe_path):
            os.mkdir(self.exe_path)
        elif sub_config.diskLimit <= 0:
            os.system('rm ' + self.exe_path + '* -r -f')

        child=None
        try:
            # user_id=str(random.randint(99000,99999))
            # group_id=str(random.randint(99000,99999))
            os.system('cp ' + sub_config.programPath + ' /exe')
            if sub_config.valgrindTestOn:
                #command = 'valgrind --tool=memcheck --leak-check=full --error-exitcode=1 --verbose' + \
                #' /exe/' + sub_config.programPath.split('/')[-1] + ' <' + sub_config.inputFile + ' >' + self.output_file

                running_time = -time.time()
                with open(sub_config.inputFile, "r") as inputFile, open(self.output_file, "w") as outputFile:
                    runExeCode = sp.call(['valgrind', '--tool=memcheck', '--leak-check=full', '--error-exitcode=1', '--verbose', '/exe/' + sub_config.programPath.split('/')[-1]], cwd = self.exe_path, stdin = inputFile, stdout = outputFile, stderr = sp.PIPE, timeout = int(sub_config.timeLimit / 1000 * Performance_Rate * 1.2 + 1))
                running_time += time.time()
                mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024
                if runExeCode != 0: 
                    return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.MEMLEK, 0, running_time * 1000 / Performance_Rate, mem, 0,
                                        'Memory Leak'), self.output_file
                    return
            else:
                user_id = str(99942)
                group_id = str(99958)
                command = '/bin/nsjail -Mo --chroot /tmp/chroot --quiet --max_cpus 1' + \
                        ' --rlimit_fsize ' + ('inf' if sub_config.diskLimit == 0 else str(int(abs(sub_config.diskLimit) / 1048576 * 3 + 1))) + \
                        ' --rlimit_nofile ' + ('65536' if sub_config.fileNumberLimit == -1 else str(sub_config.fileNumberLimit * 3 + 1)) + \
                        ' --rlimit_stack inf' + \
                        ' -t ' + str(int(sub_config.timeLimit / 1000 * Performance_Rate * 1.2 + 1)) + \
                        ' --cgroup_mem_mount ' + str(sub_config.memoryLimit) + \
                        ' --user ' + user_id + ' --group ' + group_id + \
                        ' --cwd ' + self.exe_path + \
                        ' -R /lib64 -R /lib  -B /exe /exe/' + sub_config.programPath.split('/')[-1] + \
                        ' <' + sub_config.inputFile + ' >' + self.output_file + ' 2>/dev/null'
                running_time = -time.time()
                child = sp.Popen(command, shell=True)
                child.wait()
                mem = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024
                running_time += time.time()

            if running_time > sub_config.timeLimit / 1000 * Performance_Rate:
                return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.TLE, 0, running_time * 1000 / Performance_Rate, mem, 0,
                                       ''), self.output_file
                return

            if mem > sub_config.memoryLimit:
                return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.MLE, 0, running_time * 1000 / Performance_Rate, mem, 0,
                                       ''), self.output_file
                return

        except sp.TimeoutExpired as e:
            if isinstance(child, sp.Popen):
                child.kill()
            return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.TLE, 0, sub_config.timeLimit * 1.2, mem, 0, ''), self.output_file
            return
        except sp.CalledProcessError as e:
            return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.RE, 0, 0, mem, 0, ''), self.output_file
            return
        except Exception as e:
            print('!!! Unknown error', e)
            raise e
        
        diskUsage = int(sp.check_output('du -s --exclude=' + sub_config.programPath.split('/')[-1] + ' /exe/', shell=True).decode().split()[0])
        if sub_config.diskLimit != 0 and diskUsage * 1024 > abs(sub_config.diskLimit):
            return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.DLE, 0, running_time * 1000 / Performance_Rate, mem, diskUsage, 'Too much disk usage.'), self.output_file
            return
        if sub_config.fileNumberLimit != -1:
            fileNumber = int(sp.check_output('find /exe/ -type f,d | wc -l', shell=True)) - 2
            if fileNumber > sub_config.fileNumberLimit:
                return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.DLE, 0, running_time * 1000 / Performance_Rate, mem, diskUsage, 'Too much files and directories.'), self.output_file
                return


        return_dict['testPointDetail'], return_dict['userOutput'] = jr.DetailResult(0, jr.ResultType.UNKNOWN if not isinstance(child, sp.Popen) or child.returncode == 0 else jr.ResultType.RE, 0,
                            running_time * 1000 / Performance_Rate, mem, diskUsage, ''), self.output_file
        return
