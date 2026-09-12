/* Restrictions needed when exposing PTYs to submissions. This is a targeted
 * filter, not a general syscall allowlist. Install only in the untrusted child,
 * after nsjail has mounted devpts and runner has dropped its UID. */
#ifndef ACMOJ_PTY_SECCOMP_H
#define ACMOJ_PTY_SECCOMP_H

#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/sched.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/syscall.h>

#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "PTY sandbox argument filtering requires a little-endian target"
#endif

#if defined(__x86_64__) && !defined(__ILP32__)
#define PTY_AUDIT_ARCH AUDIT_ARCH_X86_64
#elif defined(__aarch64__)
#define PTY_AUDIT_ARCH AUDIT_ARCH_AARCH64
#else
#error "PTY sandbox seccomp supports native x86-64 and AArch64 only"
#endif

#define PTY_DENY_SYSCALL(nr) \
  BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (nr), 0, 1), \
  BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)

static int install_pty_seccomp(void) {
  const unsigned namespace_flags = CLONE_NEWUSER | CLONE_NEWNS | CLONE_NEWPID |
    CLONE_NEWNET | CLONE_NEWIPC | CLONE_NEWUTS | CLONE_NEWCGROUP;
  struct sock_filter filter[] = {
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, PTY_AUDIT_ARCH, 1, 0),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
    /* x32 shares AUDIT_ARCH_X86_64 but uses different syscall numbers. Also
     * reject negative syscall numbers. Do not let either reach DEFAULT ALLOW. */
    BPF_JUMP(BPF_JMP | BPF_JGE | BPF_K, 0x40000000U, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
    /* clone3's flags are behind a pointer, inaccessible to classic seccomp.
     * ENOSYS lets glibc fall back to the filterable clone syscall. */
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_clone3, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | ENOSYS),
    PTY_DENY_SYSCALL(__NR_unshare),
    PTY_DENY_SYSCALL(__NR_setns),
    PTY_DENY_SYSCALL(__NR_mount),
    PTY_DENY_SYSCALL(__NR_umount2),
    PTY_DENY_SYSCALL(__NR_pivot_root),
    PTY_DENY_SYSCALL(__NR_fsopen),
    PTY_DENY_SYSCALL(__NR_fsconfig),
    PTY_DENY_SYSCALL(__NR_fsmount),
    PTY_DENY_SYSCALL(__NR_fspick),
    PTY_DENY_SYSCALL(__NR_open_tree),
    PTY_DENY_SYSCALL(__NR_move_mount),
    PTY_DENY_SYSCALL(__NR_mount_setattr),
    /* Ordinary fork/thread creation remains permitted. CLONE_NEWTIME is
     * available via unshare/clone3, both of which are already blocked. */
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_clone, 0, 4),
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, args[0])),
    BPF_JUMP(BPF_JMP | BPF_JSET | BPF_K, namespace_flags, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_ioctl, 0, 9),
    /* The kernel truncates ioctl requests to unsigned int. Match those same
     * low 32 bits so setting high argument bits cannot bypass the filter. */
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, args[1])),
    PTY_DENY_SYSCALL(TIOCSTI),
    PTY_DENY_SYSCALL(TIOCSETD),
    PTY_DENY_SYSCALL(TIOCCONS),
    PTY_DENY_SYSCALL(TIOCLINUX),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
  };
  struct sock_fprog program = {
    .len = sizeof(filter) / sizeof(filter[0]),
    .filter = filter,
  };
  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) return -1;
  return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program);
}

#undef PTY_DENY_SYSCALL
#endif
