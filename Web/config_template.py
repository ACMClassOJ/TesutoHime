class DataBaseConfig:
    mysql_Host = 'localhost'
    mysql_User = 'root'
    mysql_Password = 'SQL_PASSWORD'
    mysql_Database = 'OJ'

class LoginConfig:
    Login_Life_Time = 24 * 60 * 60 * 60 # s

class WebConfig:
    Problems_Each_Page = 20

class JudgeConfig:
    Judge_Each_Page = 15
    Max_Duration = 120
    Web_Server_Secret = ''

class ProblemConfig:
    Max_Code_Length = 16384 * 8

class DataConfig:
    server = ''
    key = ''

class LogConfig:
    path = 'PATH/tracker.log'
    maxBytes = 536870912

