class DataBaseConfig:
    mysql_Host = 'localhost'
    mysql_User = 'root'
    mysql_Password = 'Progynova'
    mysql_Database = 'OJ'

class LoginConfig:
    Login_Life_Time = 24 * 60 * 60 * 60 # s

class WebConfig:
    Problems_Each_Page = 2

class JudgeConfig:
    Judge_Each_Page = 15

class ProblemConfig:
    Max_Code_Length = 16384