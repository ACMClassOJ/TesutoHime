class DataBaseConfig:                     #数据库主要配置文件，一般在localhost
    mysql_Host = 'localhost'
    mysql_User = 'root'
    mysql_Password = 'Progynova'
    mysql_Database = 'OJ'

class RedisConfig:
    host = 'localhost'
    port = 6379
    password = 'Progynova'
    db = 0
    prefix = 'OJ_'

class LoginConfig:                        #登陆过期时间，单位s
    Login_Life_Time = 24 * 60 * 60 * 60 

class WebConfig:
    Problems_Each_Page = 20               #题库界面每页显示多少题目
    Block_Register = False                #暂停OJ注册

class JudgeConfig:
    Judge_Each_Page = 15                  #评测详情界面每页显示多少题目
    Max_Duration = 120                    #judger上次向web发送心跳超过这个时间判定为下线，单位s
    Web_Server_Secret = 'web_secret'      #web_secret，judger需要此密钥来向web服务器通信
                                          #建议生成随机字符串构成一个较强的密钥

class ProblemConfig:
    Max_Code_Length = 16384 * 8           #代码提交最多接受长度上限
                                          #这里为后端限制，请注意在前端js中还有限制，请一并修改

class DataConfig:
    server = 'http://192.168.1.233:8080/' #data_service_url，数据服务地址，可以是内网
                                          #一定要有http://
    key = 'data_service_key'              #data_service_key，数据服务密钥

class QuizTempDataConfig:
    server = 'http://192.168.1.233:8080/'        #quiz_service_url，填选服务地址，大多情况下与数据服务地址保持一致，可以是内网
    key = 'quiz_service_key'                     #quiz_service_key，填选服务密钥，大多情况下与数据服务密钥保持一致
    cache_dir = '/home/rbq/TesutoHime_quiz_tmp'  #quiz_cache_dir，用于解压存放填选临时文件的本地目录

class LogConfig:
    path = '/home/rbq/TesutoHime_log/tracker.log'       #web_log_url，Web服务日志存放的本地目录
    maxBytes = 536870912                                #Web服务日志保存的最大空间

class PicConfig:
    server = 'http://192.168.1.233:8080/' #pic_service_url_public，请填写可从*公网*访问的图片服务地址
    key = 'pic_service_key'               #pic_service_key，图片服务密钥