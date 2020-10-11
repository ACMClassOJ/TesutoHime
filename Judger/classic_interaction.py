import random
import sys
import os
import time
import subprocess as sp

exec_storage_path='/work/'
exec_name=''
chroot_path='/tmp/chroot'
workspace_path='/work/'

def get_mem(pid):
    return int(os.popen('cat /proc/'+str(pid)+'/statm').read().split(' ')[1])

def create_environment():
    if(not os.path.isdir(chroot_path)):
        os.mkdir(chroot_path)
    # todo: create /tmp/chroot
    # todo: create path to store exe


def run(executable_path,input_path,output_path)->(int,int):
    create_environment()
    user_id=str(random.randint(99000,99999))
    group_id=str(random.randint(99000,99999))
    command = '/testdata/nsjail -Mo --chroot /tmp/chroot --max_cpus 1 --time_limit 1 --user '+user_id+' --group '+group_id+' -R /lib64 -R /lib  -R '+executable_path+' '+executable_path+exec_name+' <'+input_path+' >'+output_path
    p=sp.Popen(command,shell=True)
    max_mem=0
    start_time=time.time()
    while p.poll() is None:
        time.sleep(2e-3)
        max_mem=max(max_mem,get_mem(p.pid))
    end_time=time.time()
    return max_mem,int((end_time-start_time)*1000)


print(run('/testdata/ans','/testdata/input.txt','/testdata/output1.txt'))