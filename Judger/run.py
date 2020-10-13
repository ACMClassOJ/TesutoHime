import threading
from Judger.api import api
from Judger.heartBeat import HeartBeat

def RunFlask(f, port):
    f(host='0.0.0.0', port=port)


global api
t1 = threading.Thread(target=RunFlask, args=(api.run, 8000,))
global HeartBeat
t2 = threading.Thread(target=HeartBeat.sendHeartBeat)
t1.start()
t2.start()
