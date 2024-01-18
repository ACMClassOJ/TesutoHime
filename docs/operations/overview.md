ACMOJ 运维文档
==============

本部分文档记述了 ACMOJ 生产环境中的一些配置方式。本文档对希望自己搭建 ACMOJ 开发环境的人员来说帮助不大。

## 整体架构

ACMOJ 由一台物理机 (评测机) 和一台虚拟机 (Web、数据服务、调度机) 构成。物理机代号为 acmoj-2023 (因 2023 年启用而得名)，虚拟机代号为 acmoj-web。两者均位于 APEX 机房的局域网中。APEX 机房的网络也可由 APEX 实验室及 ACM 队访问，内网环境不可信，**请务必做好资源的保护，防止向网络暴露无密码或弱密码的服务。**

此外，在各台机器上还可能会看到残留的对 judge{1..4} 机器的引用；这是之前使用的评测机 (四台位于 ACM 主服务器上的虚拟机，均为 1c2g，评测机编号 1–4)，因为严重的性能和可靠性问题已经不再使用。

## acmoj-web

acmoj-web (虚拟机，8c4g) 位于 ACM 班主服务器上。运维应从 acmoj 用户登录机器，此用户有 sudo 权限，不应当用于运行服务。acmoj 的 .bashrc 中有一些方便运维的配置。

OJ 代码位于 /opt/TesutoHime 中，在 acmoj 用户的 ~/TesutoHime 有指向 /opt/TesutoHime 的符号链接。在 /opt/TesutoHime/venv 中有一个 Python venv，安装了所有 web 和 scheduler 所需要的 pip package。可以用 `. ./venv/bin/activate` 进入 venv。

Web 服务由 ojweb 用户运行，apache2 的 mod_wsgi 管理。更新 OJ 代码后，应该执行 `reload-web` 来重新加载 apache2。日志位于 /var/log/oj/web。

ACMOJ 接入公网的虚拟机会向 acmoj-web:80 转发 /OnlineJudge/ 等相关路径的流量。acmoj-web:80 的服务端为 Apache+mod_wsgi，配置文件位于 /etc/apache2/sites-available/{oj,web}.conf；其中 web.conf 与本 repo 中 etc/oj_wsgi.conf 相同。oj.conf 用于分流请求到后端和存储服务器 (minio)。当 OJ 临时维护时，应修改 oj.conf 中的内容，将 apache 显示的内容由 OJ 替换为「维护中」页面 (位于 /var/www/maintenance)。

```
# 正常使用
ProxyPass /OnlineJudge/ http://127.0.1.1/OnlineJudge/
ProxyPassReverse /OnlineJudge/ http://127.0.1.1/OnlineJudge/
# Alias /OnlineJudge/ /var/www/maintenance/

# 维护中
# ProxyPass /OnlineJudge/ http://127.0.1.1/OnlineJudge/
# ProxyPassReverse /OnlineJudge/ http://127.0.1.1/OnlineJudge/
Alias /OnlineJudge/ /var/www/maintenance/
```

Minio 运行在 9000 和 9001 端口上 (**9000 对内网开放，部分对公网开放**，因为评测机需要访问；9001 只监听本机地址)。其中 9001 端口为 Web 控制台，需要访问时可以用 `ssh -L 9001:localhost:9001 oj.acm` 将其转发到运维自己的电脑上进行访问。

PostgreSQL 运行在 5432 端口上 (只监听本机地址)，同时监听 /run/postgresql/.s.PGSQL.5432。有 acmoj、ojweb 与 bak 三个用户，均为 unix socket 免密码登录。直接使用 `psql` 即可管理数据库。同时，为方便运行 scripts/ 中的脚本，在 acmoj 用户的 .bashrc 中已设好对应的 DB 环境变量，无需手动设置。

Redis 运行在 6379 端口上 (**对内网开放**，因为评测机需要访问)，有密码保护。

调度机由 ojsched 用户运行在 5100 端口上 (只监听本机地址)，使用 systemd 启动，配置文件位于 /usr/lib/systemd/system/scheduler2.service (本 repo 中的 etc/scheduler2.service)。更新代码后应使用 `reload-sched` 重启。日志位于 /var/log/oj/scheduler。调度机的日志由 logrotate 负责维护，配置文件位于 /etc/logrotate.d/ojsched。

## acmoj-2023

acmoj-2023 是一台物理机 (6 大 8 小共 14 核 20 线程，16G 内存)，无法远程开机，请务必注意。运维应从 acmoj 用户登录机器，此用户有 sudo 权限。

评测机代码位于 /home/ojrunner/TesutoHime，使用 ojrunner 用户运行，使用 systemd 启动，配置文件位于 /usr/lib/systemd/system/judger2@.service (与 repo 中的 judger2.service 有所不同)。更新代码后应使用 `sudo systemctl restart judger2@{12..19}` 重启。

评测机的工作目录位于 /var/oj/runner/{12..19} 中 (每个目录对应一台虚拟评测机，编号 5–12)，/var/oj/runner/gen 这一脚本用于生成配置文件。conf/ 为配置文件 (也是评测机的 cwd)，wd/ 为工作目录 (临时文件)，cache/ 为缓存，log/ 为日志。评测机的日志由 logrotate 负责维护，配置文件位于 /etc/logrotate.d/ojrunner。
