import random
import sys
import os
import time
import subprocess as sp
import judger_interface as ji

exec_storage_path='/work/'
exec_name=''
chroot_path='/tmp/chroot'
workspace_path='/work/'

def get_mem(pid):
    return int(os.popen('cat /proc/'+str(pid)+'/statm').read().split(' ')[1])

def create_environment():
    if(not os.path.isdir(chroot_path)):
        os.mkdir(chroot_path)
    # todo: create path to store exe


def run_instance(executable_path,input_path,output_path,memory_limit,runtime_limit)->(int,int,int):
    create_environment()
    user_id=str(random.randint(99000,99999))
    group_id=str(random.randint(99000,99999))
    command = '/testdata/nsjail -Mo --chroot /tmp/chroot --max_cpus 1 -t '+runtime_limit+' --user '+user_id+' --group '+group_id+' -R /lib64 -R /lib  -R '+executable_path+' '+executable_path+exec_name+' <'+input_path+' >'+output_path
    p=sp.Popen(command,shell=True)
    max_mem=0
    start_time=time.time()
    while p.poll() is None:
        time.sleep(2e-3)
        max_mem=max(max_mem,get_mem(p.pid))
        if(runtime_limit<time.time()-start_time):
            return max_mem,runtime_limit,ji.TLE
        if(max_mem>memory_limit):
            return max_mem,time.time()-start_time,ji.MEM
    end_time=time.time()
    # return mem_usage, time_usage, return status
    return max_mem,int((end_time-start_time)*1000),ji.UNSURE if p.returncode==0 else ji.RE

        