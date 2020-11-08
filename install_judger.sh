#!/bin/sh
apt install -y libseccomp-dev libseccomp2 seccomp protobuf-compiler libnl-3-dev libnl-route-3-dev valgrind python3 python3-pip build-essential make cmake git zsh wget curl
git clone git@github.com:cmd2001/TesutoHime.git
pip3 install -r Judger/requirements.txt
mkdir /exe/ && chmod 777 /exe/
mkdir /work/ && chmod 777 /work/
cp ./nsjail /bin
chmod 0755 /bin/nsjail