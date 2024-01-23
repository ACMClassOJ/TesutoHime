import json
import logging
import logging.handlers
from datetime import datetime
from typing import Any, Dict

from flask import request

from web.config import LogConfig
from web.realname_manager import RealnameManager
from web.session_manager import SessionManager
from web.user_manager import UserManager
from web.utils import readable_time


class Tracker:
    def log(self):
        everything: Dict[Any, Any] = {}
        username = SessionManager.get_username()
        everything['IP'] = request.remote_addr
        everything['Time'] = readable_time(datetime.now())
        everything['Username'] = username
        if username is not None and username != '':
            everything['Realname'] = RealnameManager.query_realname(UserManager.get_student_id(username))
        everything['url'] = '/'.join(request.url.split('/')[4:])
        everything['post_args'] = request.form.copy()
        if 'password' in everything['post_args']:
            del everything['post_args']['password']
        if 'code' in everything['post_args']:
            del everything['post_args']['code']
        everything['args'] = request.args
        self.tracker.info(json.dumps(everything, ensure_ascii=False))

    def __init__(self):                                  #经测试，先运行init，再运行下面的setup_log
        self.tracker = logging.getLogger(LogConfig.name)
        self.syslog = logging.getLogger()

def setup_tracker(logger_name, log_file, max_bytes, backup_count, level=logging.INFO, enable_formatter=False):
    l = logging.getLogger(logger_name)
    file_handler = logging.handlers.RotatingFileHandler(filename=log_file, maxBytes=max_bytes, backupCount=backup_count)
    if enable_formatter:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)s - %(message)s')
        file_handler.setFormatter(formatter)
    l.setLevel(level)
    l.addHandler(file_handler)

def setup_log():
    setup_tracker(LogConfig.name, LogConfig.path, LogConfig.Max_Bytes, LogConfig.Backup_Count, logging.INFO)
    setup_tracker(None, LogConfig.Syslog_Path, LogConfig.Max_Bytes, LogConfig.Backup_Count, logging.INFO, True)

tracker = Tracker()
