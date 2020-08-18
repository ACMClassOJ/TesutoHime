import pymysql
from config import *

def DB_Connect():
    return pymysql.connect(DataBaseConfig.mysql_Host, DataBaseConfig.mysql_User, DataBaseConfig.mysql_Password, DataBaseConfig.mysql_Database)
