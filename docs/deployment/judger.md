# 部署评测机

*此文档是部署文档的一部分，其中的一部分信息在[概览文档](overview.md)中提及。如果尚未阅读该文档，请先阅读[概览文档](overview.md)。*

在 judge 上创建一个用户，把 repo clone 下来:

```sh
ssh 10.0.0.4 # 登录到 judge 机
sudo apt install python3 python3-pip pkg-config autoconf bison flex libprotobuf-dev libnl-route-3-dev libtool protobuf-compiler uidmap build-essential cmake jq nix-setup-systemd
sudo adduser ojrunner
sudo -iu ojrunner
cd
git clone ...
cd TesutoHime
```

安装 Python 依赖项:

```sh
pip3 install -r judger2/requirements.txt
```

创建工作目录: (位置可自定义)

```sh
sudo mkdir -p /var/oj/runner /var/log/oj/runner /var/cache/oj/runner
sudo chown ojrunner:ojrunner /var/oj/runner /var/log/oj/runner /var/cache/oj/runner
```

生成 git clone 所需的密钥：(如果不需要 ssh clone 可以跳过)

```sh
ssh-keygen -t ed25519
```

复制并编辑配置文件，填写必需的 [cgroup 配置](#cgroup-与-pty):

```sh
cp runner.sample.yml runner.yml
vim runner.yml
```

配置 nix:

```sh
usermod -aG nix-users "$(id -nu)"
# 修改用户组后可能需要重新登录
nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
nix-channel --update
```

编译所需的二进制文件: (会编译一遍 coreutils 和 nsjail，耗时可能较长)

```sh
cd /path/to/TesutoHime/judger2/sandbox
make
```

如果你的 git 版本严格低于 2.38.0, [则需要设置全局 git 配置][git]:

[git]: https://git.kernel.org/pub/scm/git/git.git/commit/?id=6061601d9f1f1c95da5f9304c319218f7cc3ec75

```sh
sudo git config --system safe.directory '*'
```

最后，还需要配置一下 `/etc/subuid` 使得评测沙箱能够正常工作:

```sh
echo "ojrunner:100000:65536" | sudo tee -a /etc/subuid
```

启动评测机:

```sh
cd /path/to/TesutoHime
python3 -m judger2.main
```

配置 [logrotate]: 向 `/etc/logrotate.d/ojrunner` 中写入以下内容

```text
/var/log/oj/runner/*.log {
  daily
  missingok
  rotate 30
  notifempty
  create 640 ojrunner ojrunner
  compress
  delaycompress
}
```

在评测任务较多时，遇到过 linux namespaces 分配超出限制的情况，表现为 nsjail 返回 255 (clone3(2) 返回 ENOSPC)。这本是不应该的，但是不知道为什么会发生。可以提高限制来避免遇到问题：

```sh
echo 1073741824 | sudo tee /proc/sys/user/max_*_namespaces
```

[logrotate]: https://www.man7.org/linux/man-pages/man8/logrotate.8.html

## cgroup 与 PTY

需要 Linux 5.19+、原生 x86-64 或小端 AArch64，以及 user namespace、devpts 和 cgroup v2 memory/pids 支持。
升级后运行 `make -C judger2/sandbox`，重建 runner 和 nsjail。

systemd 254+：用 `systemctl edit judger2.service` 添加：

```ini
[Service]
Delegate=memory pids
DelegateSubgroup=supervisor
```

父组交给评测服务管理，服务进程放在 `supervisor` 子组；旧版 systemd 需手动配置此结构。
worker 必须使用不同的 UID，且无权管理该子树。

查看服务的 cgroup 路径：

```sh
systemctl show judger2.service --property=ControlGroup --value
```

在输出前加 `/sys/fs/cgroup`，填入 `runner.yml`：

```yaml
sandbox:
  pty: true
  cgroup_path: /sys/fs/cgroup/system.slice/judger2.service
  pids_max: 128
```

等任务结束后，运行 `systemctl daemon-reload` 和 `systemctl restart judger2.service`。
cgroup 必须配置；PTY 默认关闭，设 `pty: true` 开启。`pids_max` 限制每次运行的进程和线程总数。
内存改为统计提交进程树的峰值，包含文件缓存和内核开销，详见[沙箱说明](../dev/sandbox.md#pty-与-cgroup)。

每个沙箱最多 32 对 PTY。用 `sysctl kernel.pty.max kernel.pty.reserve kernel.pty.nr` 检查宿主机配额，
按所有并发沙箱预留容量，并保留管理员终端配额。
