from time import sleep
import requests
from config import *

class HeartBeat:
    def sendHeartBeat():
        while True:
            data = {}
            data['Server_Secret'] = My_Web_Server_Secret
            try:
                re = requests.post(Web_Server + '/heartBeat', data = data).content.decode()
            except:
                re = '-1'
            if re != '0':
                sleep(Heart_Beat_Period / 5000)
                try:
                    requests.post(Web_Server + '/heartBeat', data = data)
                except:
                    pass
            sleep(Heart_Beat_Period / 1000)