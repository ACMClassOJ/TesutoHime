# 部署 Web 端

*此文档是部署文档的一部分，其中的一部分信息在[概览文档](overview.md)中提及。如果尚未阅读该文档，请先阅读[概览文档](overview.md)。*

在 web 机 (10.0.0.2) 部署 Web 服务器。

## 事先准备

安装必备环境，终端输入

```sh
sudo apt install python3 python3-pip git wget curl mariadb-server redis-server
```

创建 OJ 用户 (用户名可自定义)

```sh
sudo adduser ojweb
```

获取项目源代码，或将服务器 ssh 公钥加入 github ssh key 或 deploy key 后输入

```sh
sudo -iu ojweb
git clone git@github.com:ACMClassOJ/TesutoHime.git
```

安装 python 运行库，命令行输入

```
cd TesutoHime
pip3 install -r web/requirements.txt
```

## 建立数据库环境

命令行输入：

```sh
sudo -u postgres psql
```

数据库名称为 OJ。

```sql
-- 此处用户名需与上面创建的 Linux 用户名一致
CREATE USER "ojweb";
-- 若要用密码登录:
-- CREATE USER "ojweb" PASSWORD 'xxxxxxxx';

CREATE DATABASE oj OWNER ojweb;
quit
```

创建数据表。

```sh
sudo -iu ojweb
cd TesutoHime
export DB='postgresql+psycopg2://ojweb@/oj'
python3 -m scripts.db.init
```

## 配置 redis

修改 redis 的配置文件（一般位于 `/etc/redis/redis.conf`），添加如下这一行来设置密码。
```
requirepass Progynova
```

## 配置 Web 服务器

创建 Web 运行日志目录、填选服务缓存目录，（路径可自定义） 下文分别称其路径为``web_log_url``、``quiz_cache_dir``

```sh
sudo mkdir -p /var/log/oj/web/ /var/cache/oj/web/
sudo chown ojweb /var/log/oj/web/ /var/cache/oj/web/
```

编写 Web 配置文件，输入

```sh
cd TesutoHime/web
cp config_template.py config.py
```

使用编辑器打开 `config.py`，填写对应参数

```python
class DatabaseConfig:
    # 数据库地址, 一般替换用户名与数据库名即可
    # 用户名要与上面的 Linux 用户名一致
    # 如果用用户名和密码登录数据库:
    # url = 'postgresql+psycopg2://username:password@localhost/oj'
    url = 'postgresql+psycopg2://ojweb@/oj'

    # 经过多少秒后，一个数据库连接将被 sqlalchemy 连接池回收。
    # 由于 mysql 服务端通常对一个连接的最长时长有限制（默认是 28800 秒），
    # 我们需要让 sqlalchemy 连接池在此之前主动作废这些已经过去很久的连接。
    # 参考 https://docs.sqlalchemy.org/en/14/core/engines.html#sqlalchemy.create_engine.params.pool_recycle
    connection_pool_recycle = 7200

class RedisConfig:
    host = 'localhost'
    port = 6379
    password = 'Progynova'
    db = 0
    prefix = 'OJ_'

class S3Config: # 文件存储配置
    # S3 反代地址
    public_url = '/OnlineJudge/'
    class Connections:
        public = {
            # 反代后面的地址，需要保证反向代理发给 s3 的 host 与之一致
            # 例如反向代理是 proxy_pass http://10.0.0.1:9000/oj-problems/;
            # 则填写 http://10.0.0.1:9000/
            'endpoint_url': 'http://localhost:9000/',
            # 见 judger2 的「配置 S3」一节
            'aws_access_key_id': 'xxxxxxxxxxxxxxxx',
            'aws_secret_access_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        }
        internal = {
            # 内网可访问即可，用于文件下载
            'endpoint_url': 'http://localhost:9000/',
            'aws_access_key_id': 'xxxxxxxxxxxxxxxx',
            'aws_secret_access_key': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        }
    class Buckets:
        # 需与调度机配置一致
        # 题目数据
        problems = 'oj-problems'
        # 提交的代码
        submissions = 'oj-submissions'
        # 图床
        images = 'oj-images'


class LoginConfig:                        #登陆过期时间，单位s
    Login_Life_Time = 24 * 60 * 60 * 60 

class WebConfig:
    Problems_Each_Page = 20               #题库界面每页显示多少题目
    Block_Register = False                #暂停OJ注册
    Contests_Each_Page = 20                #比赛页面每页显示多少比赛

class NewsConfig:
    feed = 'https://acm.sjtu.edu.cn/OnlineJudge/blog/index.json'

class SchedulerConfig:
    base_url = 'http://localhost:5100'    # 调度器 URL，内网可访问即可
    auth = 'Bearer xxxxxxxxxxxxxxxx'      # 调度器密钥，需与调度器侧配置一致 (请将 x 替换为随机数)

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
```

测试 Web 服务是否可以运行，输入

```
cd /path/to/TesutoHime
python3 -m web.main
```

在浏览器中访问 ``http://web_url:web_port/OnlineJudge/``查看是否可以访问 OJ 首页。

调度器 URL 填为 <http://10.0.0.3:5100/>，S3 public endpoint 填
http://10.0.0.1:9000，S3 public URL 填 <https://acm.sjtu.edu.cn/OnlineJudge/>。

配置 pub 机上的反向代理使得:

```
https://acm.sjtu.edu.cn/OnlineJudge/* -> http://10.0.0.2:5000/OnlineJudge/*
```

示例 nginx 配置:

```
client_max_body_size 4096M; # 最大上传文件大小为 4 GiB
location /OnlineJudge/oj-problems/ {
  proxy_pass http://10.0.0.1:9000/oj-problems/;
}
location /OnlineJudge/oj-images/ {
  proxy_pass http://10.0.0.1:9000/oj-images/;
}
location /OnlineJudge/oj-submissions/ {
  proxy_pass http://10.0.0.1:9000/oj-submissions/;
}
location /OnlineJudge/ {
  proxy_pass http://10.0.0.2:5000/OnlineJudge/;
}
```
