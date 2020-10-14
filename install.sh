#!/bin/sh
mkdir /exe/ && chmod 777 /exe/
mkdir /work/ && chmod 777 /work/
apt-get install  protobuf-compiler libnl-3-dev libnl-route-3-dev
cp ./nsjail /bin
chmod 0755 /bin/nsjail