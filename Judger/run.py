import threading
from api import api
from heartBeat import HeartBeat
from config import API_port

def RunFlask(f, port):
    f(host='0.0.0.0', port=port)


from config import Path
import os
os.chdir(Path)

global api
t1 = threading.Thread(target=RunFlask, args=(api.run, API_port,))
global HeartBeat
t2 = threading.Thread(target=HeartBeat.sendHeartBeat)
t1.start()
t2.start()