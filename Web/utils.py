import pymysql
import requests
import datetime
import time
from config import *


def db_connect():
    return pymysql.connect(host = DataBaseConfig.mysql_Host, user = DataBaseConfig.mysql_User, password = DataBaseConfig.mysql_Password,
                           database = DataBaseConfig.mysql_Database)


def unix_nano() -> int:  # Integer Unix Nano
    return int(time.time())


def unix_nano_float() -> float:  # float point time in Second
    return time.time()


def readable_time(nano) -> str:
    return str(time.strftime("%b-%d-%Y %H:%M:%S", datetime.datetime.fromtimestamp(nano).timetuple()))

def gen_page(cur_page: int, max_page: int):
    ret = []
    if cur_page != 1:
        ret.append(['<<', 1, 0])
    else:
        ret.append(['<<', 1, -1])  # -1 for disabled
    if cur_page != 1:
        ret.append(['<', cur_page - 1, 0])
    else:
        ret.append(['<', cur_page - 1, -1])  # -1 for disabled
    if max_page < 5:
        for i in range(1, max_page + 1):
            if i != cur_page:
                ret.append([str(i), i, 0])
            else:
                ret.append([str(i), i, 1])  # 1 for highlight
    else:
        if cur_page - 2 < 1:
            for i in range(1, 6):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        elif cur_page + 2 > max_page:
            for i in range(max_page - 4, max_page + 1):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        else:
            for i in range(cur_page - 2, cur_page + 3):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
    if cur_page < max_page:
        ret.append(['>', cur_page + 1, 0])
    else:
        ret.append(['>', cur_page + 1, -1])
    if cur_page < max_page:
        ret.append(['>>', max_page, 0])
    else:
        ret.append(['>>', max_page, -1])
    return ret

def gen_page_for_problem_list(cur_page: int, max_page: int, latest_page_under_11000: int):
    ret = []
    if cur_page != 1:
        ret.append(['<<', 1, 0])
    else:
        ret.append(['<<', 1, -1])  # -1 for disabled
    if cur_page != 1:
        ret.append(['<', cur_page - 1, 0])
    else:
        ret.append(['<', cur_page - 1, -1])  # -1 for disabled
    if max_page < 5:
        for i in range(1, max_page + 1):
            if i != cur_page:
                ret.append([str(i), i, 0])
            else:
                ret.append([str(i), i, 1])  # 1 for highlight
    else:
        if cur_page - 2 < 1:
            for i in range(1, 6):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        elif cur_page + 2 > max_page:
            for i in range(max_page - 4, max_page + 1):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        else:
            for i in range(cur_page - 2, cur_page + 3):
                if i != cur_page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
    if cur_page < max_page:
        ret.append(['>', cur_page + 1, 0])
    else:
        ret.append(['>', cur_page + 1, -1])
    if cur_page < max_page:
        ret.append(['>>', max_page, 0])
    else:
        ret.append(['>>', max_page, -1])
    ret.append(['#',latest_page_under_11000, 0])
    return ret


def ping(url: str) -> bool:
    url = url + '/ping'
    for i in range(0, 3):
        try:
            ret = requests.get(url).content.decode()  # Fixme: trust self-signed SSL
            if ret == '0':
                return True
        except requests.exceptions:
            pass
    return False
