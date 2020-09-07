import threading
from Judger.judge_api import judge_api
from Judger.isBusy_api import isBusy_api


def RunFlask(f, port):
    f(host='0.0.0.0', port=port)


global judge_api
t1 = threading.Thread(target=RunFlask, args=(judge_api.run, 5000,))
global isBusy_api
t2 = threading.Thread(target=RunFlask, args=(isBusy_api.run, 5001,))
t1.start()
t2.start()
