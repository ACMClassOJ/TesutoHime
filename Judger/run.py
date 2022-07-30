import threading
from api import api
from heartBeat import HeartBeat
from config import API_port

def RunFlask(f, port):
    f(host='0.0.0.0', port=port)


from config import working_dir
import os
os.chdir(working_dir)

if os.path.exists('BusyFlag'):
   os.remove('BusyFlag')

global api
t1 = threading.Thread(target=RunFlask, args=(api.run, API_port,))
global HeartBeat
t2 = threading.Thread(target=HeartBeat.sendHeartBeat)
t1.start()
t2.start()