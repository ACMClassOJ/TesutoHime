import pymysql
import requests
import datetime
import time
from config import *


def DB_Connect():
    return pymysql.connect(DataBaseConfig.mysql_Host, DataBaseConfig.mysql_User, DataBaseConfig.mysql_Password, DataBaseConfig.mysql_Database)

def UnixNano() -> int: # Inteager Unix Nano
    return int(time.time())

def UnixNanoFloat() -> float: # float point time in Second
    return time.time()


def Readable_Time(nano) -> str:
    return time.strftime("%b-%d-%Y %H:%M:%S", datetime.datetime.fromtimestamp(nano).timetuple())

def Gen_Page(cur_Page: int, max_Page: int):
    ret = []
    if cur_Page != 1:
        ret.append(['<', cur_Page - 1, 0])
    else:
        ret.append(['<', cur_Page - 1, -1]) # -1 for disabled
    if max_Page < 5:
        for i in range(1, max_Page + 1):
            if i != cur_Page:
                ret.append([str(i), i, 0])
            else:
                ret.append([str(i), i, 1]) # 1 for highlight
    else:
        if cur_Page - 2 < 1:
            for i in range(1, 6):
                if i != cur_Page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        elif cur_Page + 2 > max_Page:
            for i in range(max_Page - 4, max_Page + 1):
                if i != cur_Page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
        else:
            for i in range(cur_Page - 2, cur_Page + 3):
                if i != cur_Page:
                    ret.append([str(i), i, 0])
                else:
                    ret.append([str(i), i, 1])
    if cur_Page < max_Page:
        ret.append(['>', cur_Page + 1, 0])
    else:
        ret.append(['>', cur_Page + 1, -1])
    return ret

def Ping(url: str) -> bool:
    url = url + '/ping'
    for i in range(0, 3):
        try:
            ret = requests.get(url) # todo: trust self-signed SSL
            if ret == '0':
                return True
        except:
            pass
    return False
