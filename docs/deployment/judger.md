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

在评测任务较多时，遇到过 linux namespaces 分配超出限制的情况，表现为 nsjail 返回 255 (clone3(2) 返回 ENOSPC)。这本是不应该的，但是不知道为什么会发生。可以提高限制来避免遇到问题：

```sh
echo 1073741824 | sudo tee /proc/sys/user/max_*_namespaces
```

[logrotate]: https://www.man7.org/linux/man-pages/man8/logrotate.8.html
