# 部署概览

此部署指南将假设有五台互相独立的 (虚拟) 服务器，分别用来做数据服务、
Web、调度机、评测机和反向代理。

*本文档默认服务器是 debian 及其衍生版，如果你使用的是其他发行版，请自行安装对应的软件包。*

假设五台服务器的名称及网络配置如下：

| 名称 | 用途 | IP |
| ---- | ---- | -- |
| data | 数据服务 | 10.0.0.1 |
| web | Web 服务器 | 10.0.0.2 |
| sched | 调度机 | 10.0.0.3 |
| judge | 评测机 | 10.0.0.4 |
| pub | 反向代理 | 202.120.61.16 2001:da8:8000:6e40:202:120:61:16 |

在实际生产中，data web sched 三台服务器可以合并。

## 1 部署 S3 服务

参见[部署 S3 服务文档](S3.md)。

## 2 部署 Web 端

参见[部署 Web 端文档](web.md)。

## 3 配置 Redis

我们希望 Web 和调度机使用不同的 redis 命名空间，
所以我们在调度机和评测机上将 redis 的 database 配置为 1，
而在 Web 上配置为 0。(也可以在两台机器上跑两个 redis。)

为了让评测机和调度机访问到 redis，需要在 `/etc/redis/redis.conf`
中 **注释掉** 如下一行:

```
bind 127.0.0.1 ::1
```

意为 redis 只对本机开放。请做好 redis 端口的防火墙配置 (仅对内网开放),
否则机器可能会被 get shell。

## 4 部署调度机

参见[部署调度机文档](scheduler.md)。

## 5 部署评测机

参见[部署评测机文档](judger.md)。

## 6 向数据库中添加评测机

向数据库中添加评测机可以让 Web 知道这台评测机的存在，从而显示其状态。
首先登录到 Web:

```sh
ssh 10.0.0.2 # 登录到 web 机
cd /path/to/TesutoHime
# 下面这行是设置数据库连接，具体连接参数请参考 Web 部署文档
export DB='mysql+pymysql://ojweb@/OJ?unix_socket=/run/mysqld/mysqld.sock'
python3 -m scripts.add_runner
```

根据提示操作即可。
