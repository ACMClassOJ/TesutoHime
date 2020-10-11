from flask import Flask
from time import sleep
import requests
from Judger.config import *

heartBeat = Flask('APP')

@heartBeat.route('/')
def sendHeartBeat():
    while True:
        data = {}
        data['Server_Secret'] = Web_Server_Secret
        re = requests.post(Web_Server, data = data)
        if re != '0':
            sleep(Heart_Beat_Period / 5000)
            requests.post(Web_Server, data = data)
        sleep(Heart_Beat_Period / 1000)