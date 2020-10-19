import threading
from Judger.api import api
from Judger.heartBeat import HeartBeat
from Judger.config import API_port

def RunFlask(f, port):
    f(host='0.0.0.0', port=port)


global api
t1 = threading.Thread(target=RunFlask, args=(api.run, API_port,))
global HeartBeat
t2 = threading.Thread(target=HeartBeat.sendHeartBeat)
t1.start()
t2.start()