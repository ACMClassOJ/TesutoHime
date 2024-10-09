# Judger

*由于目前 judger 模块已经迭代到第二代，因此也称作 judger2。*

Judger 模块相关代码位于 [`judger2/`](../../judger2/) 目录下。本文档中，除非特殊说明，否则所有涉及的文件都以 `judger2` 目录为基础。

## 评测流程

评测将分为三个步骤（位于 [`steps/`](../../judger2/steps/) 下：

1. 编译。此阶段中，会先准备好用户的文件，然后将题目的辅助文件拷贝到工作目录下（此过程会检查文件冲突）。具体参见 [`steps/compile_.py`](../../judger2/steps/compile_.py)。
1. 运行。具体参见 [`steps/run.py`](../../judger2/steps/run.py)。
1. 评分。具体参见 [`steps/check.py`](../../judger2/steps/check.py)。

## 评测环境

评测环境使用 [Nix][nix] 管理，配置文件位于 [`sandbox/stdenv`](../../judger2/sandbox/stdenv/) 下。Nix 可以声明式地描述评测环境的细节，便于部署和管理，同时可以独立于操作系统进行评测环境的升级。

[nix]: https://nixos.org/

评测过程中会用到多个不同的环境，这些环境在代码中称作 profile：

- 标准环境（std）：用于编译、运行 interactor 和 checker、运行 verilog 等
- libc 环境：仅包含 libc，用于运行选手提交的 C++ 程序
- Valgrind 环境：仅包含 libc 和 valgrind，用于启用 Valgrind 的测试点
- Python 环境：仅包含 Python，用于运行选手提交的 Python 程序

每个环境是一个目录（`stdenv/profiles/[profile name]/result`），这个目录下利用符号链接构建了一个运行时使用的文件系统，这些符号链接指向 `/nix/store` 下软件包里的文件。当需要使用这个环境时，会将这个目录作为根目录执行其他程序。在构建环境时会同时生成这个环境需要的软件包（derivation）列表，存储在 `profiles/[profile name]/requisites` 中。运行时会通过 [`stdenv/bin/nsjail`](../../judger2/sandbox/stdenv/bin/nsjail) 将这些 `/nix` 下的目录挂载到运行环境中。因此，运行时的环境会包含且仅包含 nix 描述中的文件。

除了 nixpkgs 的包之外，还使用了这些自定义包：

- testlib.h
- 预编译的 &lt;bits/stdc++.h&gt;
- [checker](../../judger2/checker/)
- 将 /etc/resolv.conf 链接至 /acmoj/resolv.conf 以便运行时覆盖
- /etc/ssh/ssh_config 和 /etc/passwd 用于 ssh git clone

评测环境还提供了两个脚本（使用前需先安装 nix 并配置 nixpkgs 源）：

- `stdenv/bin/shell`：模拟评测环境启动一个 shell。此程序会自动将工作目录挂载到环境中，因此，如果希望测试一个程序在评测环境中的行为，可以在程序所在目录中运行此脚本。
- `stdenv/bin/generate-versions`：输出标准环境中编译器和运行时的版本信息。

重新构建评测环境之后，由于 nix 的特性，系统库的路径可能会发生改变，此时需要重新构建所有 checker 和 interactor 等题目数据中预先编译的二进制：

```sh
python3 -m scripts.rebuild_artifacts
```

ACMOJ 的环境配置参考了 [洛谷][luogu-env] 和 [Hydro][hydro-env] 的配置（同样使用 nix）。

[luogu-env]: https://github.com/luogu-dev/judge-env
[hydro-env]: https://github.com/hydro-dev/nix-channel/blob/master/judge.nix

## 沙箱

judger2 使用了沙箱技术，以保证评测机安全，并限制资源占用。具体参见 [sandbox 文档](sandbox.md)。

## 文件缓存

judger2 会将从 s3 上下载的文件缓存在本地，以减少对 s3 的访问。

如果缓存的文件在一天内没有被访问，judger2 会自动删除该文件。如果文件在一天内被访问了，judger2 会保留该文件。

## 评测机分组

评测机支持分组调度。在 `runner.yml` 配置中，`group` 项即为调度组，默认所有题目位于 `default` 组中。可以在题目配置中更改 `RunnerGroup` 来使该题目相关的任务被分配到对应的调度组，评测机不会运行其他组的任务。
