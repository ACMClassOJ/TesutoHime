import threading
from web import web
from api import api


def RunFlask(f, port):
    f(port=port)


global web
t1 = threading.Thread(target=RunFlask, args=(web.run, 5000,))
global api
t2 = threading.Thread(target=RunFlask, args=(api.run, 5001,))
t1.start()
t2.start()
