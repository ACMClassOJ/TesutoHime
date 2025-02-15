class DatabaseConfig:
    # 数据库地址, 一般替换 username 与 database 即可
    url = 'postgresql+psycopg2://username@/database'

    # 经过多少秒后，一个数据库连接将被 sqlalchemy 连接池回收。
    # 由于 mysql 服务端通常对一个连接的最长时长有限制（默认是 28800 秒），
    # 我们需要让 sqlalchemy 连接池在此之前主动作废这些已经过去很久的连接。
    # 参考 https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine.params.pool_recycle
    connection_pool_recycle = 7200

class RedisConfig:
    host = 'localhost'
    port = 6379
    username = 'web'
    password = 'Progynova'
    db = 0
    prefix = 'web:'


class S3Config:
    public_url = 'https://acm.sjtu.edu.cn/OnlineJudge/'
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


class LoginConfig:                        #登录过期时间，单位s
    Login_Life_Time = 24 * 60 * 60 * 60

class WebConfig:
    Problems_Each_Page = 20               #题库界面每页显示多少题目
    Block_Register = False                #暂停OJ注册
    Contests_Each_Page = 20               #比赛页面每页显示多少比赛
    Courses_Each_Page = 20

class NewsConfig:
    link = 'https://acm.sjtu.edu.cn/OnlineJudge/blog/'
    feed = 'https://acm.sjtu.edu.cn/OnlineJudge/blog/index.json'

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
    log_dir = '/var/log/oj/web'

class JAccountConfig:
    CLIENT_ID = 'YOUR JACCOUNT CLIENT ID'
    CLIENT_SECRET = 'YOUR JACCOUNT CLIENT SECRET'
    AUTHORIZATION_BASE_URL = 'https://jaccount.sjtu.edu.cn/oauth2/authorize'
    TOKEN_URL = 'https://jaccount.sjtu.edu.cn/oauth2/token'
    LOGOUT_URL = 'https://jaccount.sjtu.edu.cn/oauth2/logout'
    PROFILE_URL = 'https://api.sjtu.edu.cn/v1/me/profile'
