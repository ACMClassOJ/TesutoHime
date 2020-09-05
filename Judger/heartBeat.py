from flask import Flask
import requests
from config import *

heartBeat = Flask('APP')

def sendHeartBeat():
    re = requests.post(, )