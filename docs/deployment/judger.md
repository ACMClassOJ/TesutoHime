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

复制并编辑配置文件:

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

在评测任务较多时，遇到过 linux namespaces 分配超出限制的情况，表现为 nsjail 返回 255 (clone3(2) 返回 ENOSPC)。应先排查未清理的进程和命名空间，并按实际并发需求设置有界限制。不要通过无限提高配额来掩盖泄漏。

[logrotate]: https://www.man7.org/linux/man-pages/man8/logrotate.8.html

## 可选 PTY 支持

PTY 默认关闭。如果评测程序需要使用 `openpty()` 或 `forkpty()`，可以按下面的步骤开启。
如果只想使用 cgroup 统计和限制内存，也按下面的步骤配置，但保留 `pty: false`。
先确认评测机满足这些要求：

- Linux 5.19 或更新版本，支持 user namespace、devpts 和 cgroup v2 的 memory/pids 控制器及 `memory.peak`。
- runner 使用原生 x86-64 或小端 AArch64 架构，内核已安装安全更新。
- 宿主机上的评测程序使用 Python 3.14。
- 评测服务账号有权管理一个 cgroup 子树，worker UID 无权访问它。
  评测服务和 worker 必须使用不同的 UID。

先运行 `make -C judger2/sandbox`，重新编译 runner 和构建脚本指定版本的 nsjail。
runner 需要安装新增的系统调用过滤器，所以只复制 `pty.cfg` 不能启用 PTY。

如果使用 systemd 254 或更新版本和仓库里的 `judger2.service`，
运行 `systemctl edit judger2.service`，加入：

```ini
[Service]
Delegate=memory pids
DelegateSubgroup=supervisor
```

先保持 PTY 关闭，重新加载 systemd 配置，等当前任务结束后重启服务。
`DelegateSubgroup` 会把服务进程放进 `supervisor` 子组，让父组不包含进程，
这样评测程序才能在父组下创建任务 cgroup。
旧版 systemd 需要手动安排同样的结构：父组交给评测服务管理，服务进程放进单独的子组。

用下面的命令查看服务的 cgroup 路径：

```sh
systemctl show judger2.service --property=ControlGroup --value
```

在输出路径前加上 `/sys/fs/cgroup`，就是下面 `cgroup_path` 要填写的值，通常是
`/sys/fs/cgroup/system.slice/judger2.service`。
评测程序会在创建任务 cgroup 前启用 memory/pids 控制器，重启后也会自动处理。
这里的权限只给评测服务账号，不要让 worker 能写宿主机的 cgroup 根目录，也不要关闭 namespace 隔离。

然后修改 `runner.yml`：

```yaml
sandbox:
  pty: true
  cgroup_path: /sys/fs/cgroup/system.slice/judger2.service
  pids_max: 128
  memory_overhead_bytes: 67108864
```

改好后，等当前任务结束再重启服务。控制器缺失、权限不足、挂载失败或过滤器安装失败时，
评测程序会报错并中止这次运行。上面的进程数和额外内存限额只是示例，需要用实际构建任务确认是否够用。

配置 `cgroup_path` 后，显示的内存改为整个任务 cgroup 的峰值，包括子进程、runner、
文件缓存和内核开销，和原来的 RSS 统计口径不同。
`memory_overhead_bytes` 只是内核强制终止前的余量，统计峰值超过题目内存限制仍会判 MLE。
未配置 cgroup 时保留原来的统计方式。

每个沙箱最多使用 32 对 PTY。设置宿主机的 `kernel.pty.max` 时，要算上所有并发沙箱，
保留 `kernel.pty.reserve`，也给管理员登录等操作留些余量。
可以用 `sysctl kernel.pty.max kernel.pty.reserve kernel.pty.nr` 查看上限、保留数量和当前用量。
