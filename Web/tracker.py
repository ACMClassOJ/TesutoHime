from flask import request
import logging, json, logging.handlers
from sessionManager import Login_Manager
from referenceManager import Reference_Manager
from config import LogConfig
from utils import *

class Tracker:
    def __init__(self):
        logging.basicConfig(filename=LogConfig.path, level=logging.INFO)
        logging.handlers.RotatingFileHandler(filename=LogConfig.path, maxBytes=LogConfig.maxBytes)

    def log(self, drop_args = False):
        everything = {}
        everything['IP'] = request.remote_addr
        everything['Username'] = Login_Manager.get_username()
        everything['Realname'] = Reference_Manager.Query_Realname(everything['Username'])
        everything['url'] = request.url
        everything['post_args'] = request.form
        if not drop_args:
            everything['args'] = request.args
        else:
            everything['args'] = {}
        logging.info(json.dumps(everything))

tracker = Tracker()