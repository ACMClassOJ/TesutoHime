# 数据库地址, 一般替换 username 与 database 即可
mysql_connection_string = 'mysql+pymysql://username@/database?unix_socket=/run/mysqld/mysqld.sock'

# 经过多少秒后，一个 mysql 连接将被 sqlalchemy 连接池回收。
# 由于 mysql 服务端通常对一个连接的最长时长有限制（默认是 28800 秒），
# 我们需要让 sqlalchemy 连接池在此之前主动作废这些已经过去很久的连接。
# 参考 https://docs.sqlalchemy.org/en/14/core/engines.html?highlight=cycle#sqlalchemy.create_engine.params.pool_recycle
mysql_connection_pool_recycle = 7200

class RedisConfig:
    host = 'localhost'
    port = 6379
    password = 'Progynova'
    db = 0
    prefix = 'OJ_'


class S3Config:
    public_url = 'https://acm.sjtu.edu.cn/OnlineJudge/compiler/'
    class Connections:
        public = {
            'endpoint_url': 'http://localhost:9000/',
            'aws_access_key_id': 'xxxxxxxxxxxxxxxx',
            'aws_secret_access_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        }
        internal = {
            'endpoint_url': 'http://localhost:9000/',
            'aws_access_key_id': 'xxxxxxxxxxxxxxxx',
            'aws_secret_access_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        }
    class Buckets:
        problems = 'oj-problems'
        submissions = 'oj-submissions'
        images = 'oj-images'


class LoginConfig:                        #登陆过期时间，单位s
    Login_Life_Time = 24 * 60 * 60 * 60 

class WebConfig:
    Problems_Each_Page = 20               #题库界面每页显示多少题目
    Block_Register = False                #暂停OJ注册

class SchedulerConfig:
    base_url = 'http://localhost:5100'
    auth = 'Bearer xxxxxxxxxxxxxxxx'

class JudgeConfig:
    Judge_Each_Page = 15                  #评测详情界面每页显示多少题目
    Max_Duration = 120                    #judger上次向web发送心跳超过这个时间判定为下线，单位s
    Web_Server_Secret = 'web_secret'      #web_secret，judger需要此密钥来向web服务器通信
                                          #建议生成随机字符串构成一个较强的密钥

class ProblemConfig:
    Max_Code_Length = 16384 * 8           #代码提交最多接受长度上限
                                          #这里为后端限制，请注意在前端js中还有限制，请一并修改


class QuizTempDataConfig:
    cache_dir = '/var/cache/oj/web'       #quiz_cache_dir，用于解压存放填选临时文件的本地目录

class LogConfig:
    name = 'tracker'                                    #Web服务日志名称
    path = '/var/log/oj/web/tracker.log'                #web_log_url，Web服务日志存放的本地目录
    Syslog_Path = '/var/log/oj/web/syslog.log'          #sys_log_url，其他系统服务日志存放的本地目录
    Max_Bytes = 134217728                               #Web服务日志保存的最大空间
    Backup_Count = 3                                    #Web服务需要保存多少份滚动日志。
                                                        #例如当前日志写入tracker.log, maxBytes为128M，那么当128M被写满时，
                                                        #最早的日志将被写入tracker.log.1；tracker.log.2等依此类推，直到最早的日志被废弃
