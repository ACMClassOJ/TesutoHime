from flask import request
import logging, json, logging.handlers
from sessionManager import Login_Manager
from referenceManager import Reference_Manager
from userManager import User_Manager
from config import LogConfig
from utils import *

class Tracker:
    def __init__(self):
        logging.basicConfig(filename=LogConfig.path, level=logging.INFO)
        logging.handlers.RotatingFileHandler(filename=LogConfig.path, maxBytes=LogConfig.maxBytes)

    def log(self):
        everything = {}
        everything['IP'] = request.remote_addr
        everything['Time'] = Readable_Time(UnixNano())
        everything['Username'] = Login_Manager.get_username()
        everything['Realname'] = Reference_Manager.Query_Realname(str(User_Manager.Get_Student_ID(str(everything['Username']))))
        everything['url'] = request.url.split('/')[-1]
        everything['post_args'] = request.form.copy()
        if 'password' in everything['post_args']:
            del everything['post_args']['password']
        if 'code' in everything['post_args']:
            del everything['post_args']['code']
        everything['args'] = request.args
        logging.info(json.dumps(everything))

tracker = Tracker()