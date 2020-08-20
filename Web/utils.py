import pymysql
import datetime
import time
from config import *

def DB_Connect():
    return pymysql.connect(DataBaseConfig.mysql_Host, DataBaseConfig.mysql_User, DataBaseConfig.mysql_Password, DataBaseConfig.mysql_Database)

def UnixNano() -> float: # float point time in Second
    return time.time()

