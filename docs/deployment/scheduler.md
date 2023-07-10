# 部署调度机

*此文档是部署文档的一部分，其中的一部分信息在[概览文档](overview.md)中提及。如果尚未阅读该文档，请先阅读[概览文档](overview.md)。*

在 sched 上创建一个用户，把 repo clone 下来:

```sh
ssh 10.0.0.3 # 登录到 sched 机
sudo apt install python3 python3-pip
sudo adduser ojsched
sudo -iu ojsched
cd
git clone ...
cd TesutoHime
```

安装 Python 依赖项:

```sh
pip3 install -r scheduler2/requirements.txt
```

创建工作目录: (位置可自定义)

```sh
sudo mkdir -p /var/oj/scheduler /var/log/oj/scheduler /var/cache/oj/scheduler
sudo chown ojsched:ojsched /var/oj/scheduler /var/log/oj/scheduler /var/cache/oj/scheduler
```

复制并编辑配置文件:

```sh
cp scheduler.sample.yml scheduler.yml
vim scheduler.yml
```

其中 Web URL 填 <http://10.0.0.2:5000>，S3 URL 填 <http://10.0.0.1:9000>。

运行调度机:

```sh
cd /path/to/TesutoHime
python3 -m scheduler2.main
```

配置 [logrotate] (自动归档、压缩、删除日志文件): 向 `/etc/logrotate.d/ojsched` 中写入以下内容

```
/var/log/oj/scheduler/*.log {
  daily
  missingok
  rotate 30
  notifempty
  create 640 ojsched ojsched
  compress
  delaycompress
}
```

[logrotate]: https://www.man7.org/linux/man-pages/man8/logrotate.8.html
