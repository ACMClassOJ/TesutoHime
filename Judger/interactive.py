#!/bin/python3
import subprocess as sp
import os
import fcntl
import time
print("????????????????")
cmd = "/home/test/test_program/nsjail -Mo --chroot / --user 99999 --group 99999 -- /home/test/test_program/ans"
echo = sp.Popen(cmd,stdin=sp.PIPE,stdout=sp.PIPE,universal_newlines=True,shell=True)
fd=echo.stdout.fileno()
fl=fcntl.fcntl(fd,fcntl.F_GETFL)
fcntl.fcntl(fd,fcntl.F_SETFL,fl|os.O_NONBLOCK)
echo.stdin.write("233\n")
echo.stdin.flush()

s=""
time.sleep(1e-1)
while True:
    try:
        s+=os.read(fd,1).decode("utf-8")
    except:
        break
print('=========abc==========='+s[:-1]+'================abc==========')
echo.stdin.write(str(int(s[:-1],)*2)+'\n')
echo.stdin.flush()
time.sleep(1e-3)
while True:
    try:
        s+=os.read(fd,1).decode("utf-8")
    except:
        break
print('=========def==========='+s[:-1]+'================abc==========')
