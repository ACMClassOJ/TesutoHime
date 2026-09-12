# Sandbox

## 评测沙箱概览

`judger2/sandbox` 里的评测沙箱利用了一系列 Linux syscall
来实现对系统安全的保护。

```mermaid
graph TD

subgraph 评测机
subgraph 非特权用户
subgraph 命名空间沙箱
subgraph setuid
用户输入程序
end
end
end
end
```

## 非特权用户

总不会有人用 root 去跑用户输入的程序……吧？

## 命名空间沙箱

我们用 Google 的 [nsjail] 来实现以下功能:

- 最长时间限制 (时限 +1s)
- chroot (其实是 [pivot_root(2)][pivot-root])
  - 禁止执行 /bin 和 /usr/bin 里的二进制
  - 默认不挂载 /proc /sys /tmp；只暴露所需的 /dev 设备
  - 禁止提交的程序访问输入输出文件
  - 限制对文件的写操作
- 限制网络访问
- 限制至多使用一个 cpu 核 (防止多线程加速)

在底层，主要使用的是 [namespaces(7)][ns] API。

[nsjail]: https://github.com/google/nsjail
[pivot-root]: https://man7.org/linux/man-pages/man2/pivot_root.2.html
[ns]: https://man7.org/linux/man-pages/man7/namespaces.7.html

## 可选 PTY 支持

`runner.yml` 中的 `sandbox.pty` 默认为 `false`。开启时，每次
`run_with_limits()` 都创建独立的 devpts 文件系统，包含至多 32 对 PTY。
`/dev/ptmx` 是指向该实例 `pts/ptmx` 的符号链接；不绑定宿主机的终端设备。
从而即使不同任务使用相同的 worker UID，也无法通过 `/dev/pts` 访问其他任务的终端。
`std`、`libc`、`python` 和 `valgrind` 使用相同的隔离措施。

配置文件 `judger2/sandbox/pty.cfg` 必须在 nsjail 的其他参数之前加载，因为
`--config` 会覆盖之前已解析的配置。profile 不得挂载 `/dev`，补充挂载不得覆盖
`/dev/pts` 或 `/dev/ptmx`。文件系统挂载失败时，不执行用户程序。

`runner.c` 在子进程切换到 worker UID 后安装 `pty_seccomp.h` 中的过滤器。
过滤器保留普通 fork、线程和终端操作，禁止新建命名空间、修改挂载、切换终端行规程
（`TIOCSETD`）以及 `TIOCSTI`、`TIOCCONS`、`TIOCLINUX`。`clone3` 返回
`ENOSYS`，让支持回退的 libc 使用可过滤 flags 的 `clone`。支持的架构为原生
x86-64 和小端 AArch64；其他 syscall ABI（包括 x86-64 上的 i386 和 x32）被拒绝。
过滤 ioctl 参数时按内核语义检查低 32 位。安装失败时也不执行用户程序。
这是用于 PTY 的专项过滤器，不是完整的 syscall 白名单，也不消除共享内核的风险。

配置 `sandbox.cgroup_path` 后，每次运行都会使用独立的 cgroup，开启内存统计和
memory/pids 限制；即使 PTY 关闭也会生效。开启 PTY 则必须配置这个路径。
内存占用读取父 cgroup 的 `memory.peak`，包含整个任务进程树的峰值，
nsjail 删除子 cgroup 后仍能读取，runner 没来得及写结果文件时也能统计。
这需要支持 `memory.peak` 的内核（Linux 5.19 起提供）。

这个数值包含 runner、文件缓存和内核记账的开销，不再是单个进程的 RSS，
也不会减去一个固定的开销估计值。峰值超过题目内存限制，或发生 cgroup OOM，都返回 MLE。
内核强制上限仍是题目内存限制加 `sandbox.memory_overhead_bytes`；这部分是强制终止前的余量，
不会从统计结果中扣除，也不会放宽 MLE 判定。swap 禁用，进程（含线程）上限由 `sandbox.pids_max` 指定。
没有配置 cgroup 时，仍使用 runner 返回的 `ru_maxrss`，它无法反映整个进程树的同时占用。
取消时先杀死 cgroup 内所有进程，再终止并回收 nsjail；正常结束与超时也会清理整个
进程树和 cgroup。cgroup 控制文件不挂载进沙箱。

PTY 仍占用宿主机的全局配额。部署时需要根据整个宿主机上同时运行的沙箱数量
（包括编译器、interactor 和 checker）预留容量，不能只计算 judger 进程数量。
普通 stdin/stdout 仍为文件或管道，不会自动成为终端。

部署步骤见 [评测机部署文档](../deployment/judger.md#可选-pty-支持)。

## setuid 沙箱 (aka runner.c)

在包着一层 nsjail 的情况下，我们没办法精确地测量用户程序的执行用时和内存使用，
因为 Linux 没有简单的办法在进程退出后获取任意进程的资源使用情况。
因此，我们在 nsjail 里面跑一个我们自己的小程序用来测量这些参数。
这个小程序就是 runner.c。现在配置了 cgroup 时，内存统计改由 cgroup 完成，
runner 仍负责记录用时和退出状态。它将测量结果输出到一个文件里 (因为
stdout 和 stderr 都有可能要用)，而这个文件又不希望被用户执行的程序访问到
(否则用户就可以自己写这个文件然后直接消除 TLE 和 MLE 了)。
因此，我们让 runner.c 再 drop 一次 privilege，让它 [setuid(2)][suid]
到一个权限更低的用户上去，再执行用户程序;
更改测量结果文件的权限使得新用户无法打开它。
而这时候 group 并没有变化，所以依然可以借着 group
的权限写一些中间过程所需要的文件 (e.g. 编译产物, 数据文件, etc.)

那这个 setuid 应该切换到什么用户? 整个 runner 是在一个 nsjail 造出的新的
[user namespace][user-ns-lwn] 里面的，而且评测机主进程显然并不是以 root 运行的;
我们也不希望评测机本身能借助 (强行给它的) CAP_SETUID 切换到其他用户,
否则它直接一个 `setuid(0)` 就成 root 了。

幸好，我们可以用 [subuid] 将一大堆 user id 在 user namespace
里全部都映射到外面的评测机用户上，这样给 runner 一个 CAP_SETUID
之后它就可以切到权限更低的用户上了。我们在安装指南里用到的:

```
ojrunner:100000:65536
```

就是将 100000\~165535 这 65536 个 userid 全部分配给 ojrunner 这个用户，
让它能在 user namespace 里创建这些 userid 的映射。
在评测机里，我们只用到了这些 uid 中的一个，在默认配置下就是 100001。
我们将沙箱内的 uid=65534 映射到沙箱外的 uid=100001, 然后在沙箱里让
runner setuid 到 65534 再执行用户程序，就可以防止用户程序乱搞评测机状态了。

[suid]: https://man7.org/linux/man-pages/man2/setuid.2.html
[user-ns-lwn]: https://lwn.net/Articles/532593/
[subuid]: https://www.funtoo.org/LXD/What_are_subuids_and_subgids%3F

## 关于时间限制

评测机共有这样几个时间限制:

0. 任何评测任务 (JudgeTask) 用时不得超过一个小时 (scheduler 实现)。
   这是为了防止评测机出现极端意外情况而设置的。
0. nsjail 的时间限制: 规定的时间限制 +1 s。
   因为 runner 的限制不是硬限制，所以 nsjail 这里还需要卡一下，防止有人卡评测。
0. runner 的时间限制: 规定的时间限制 +1 ms。
   通过 [setitimer(2)][setitimer] 实现，用户程序可以取消这个时间限制。
   几乎所有情况下这个时间限制都是好使的，所以 nsjail 的时限不会真正触发。
   这个时限到了之后，runner 主进程仍在运行，仍然能收集精确的时间和内存信息，
   以及程序返回值的信息。而 nsjail 的时限到了之后，runner 会被一起干掉，
   只能通过 Python 获得一个不精确的信息。

[setitimer]: https://man7.org/linux/man-pages/man2/setitimer.2.html

## 关于几个沙箱的测试程序

### mem.c

会占用一些内存，然后输出自己的内存占用情况。用来测量评测机内存测量的
overhead。

注意对比的时候不能直接对比评测机和它输出的内存占用，两者一定是一样的；
要对比评测机运行它和它在评测机外面运行时的内存占用。

### test.s

直接调用 _exit(2) 退出程序。理论上应该用时接近为
0，用来测量评测机时间测量的 overhead。
