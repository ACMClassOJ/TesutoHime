import pymysql
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
    return time.strftime("%b-%d-%Y %H:%M:%S", datetime.fromtimestamp(nano).timetuple())
