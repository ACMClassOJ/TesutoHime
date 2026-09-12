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

static int install_pty_seccomp(void) {
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
    /* A new user namespace would grant capabilities to mount extra devpts
     * instances. Privileged mount and namespace operations are left to the
     * kernel's capability checks. */
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_clone, 1, 0),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_unshare, 0, 4),
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, args[0])),
    BPF_JUMP(BPF_JMP | BPF_JSET | BPF_K, CLONE_NEWUSER, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_ioctl, 0, 3),
    /* The kernel truncates ioctl requests to unsigned int. Match those same
     * low 32 bits so setting high argument bits cannot bypass the filter. */
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, args[1])),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, TIOCSETD, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
  };
  struct sock_fprog program = {
    .len = sizeof(filter) / sizeof(filter[0]),
    .filter = filter,
  };
  if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) return -1;
  return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program);
}

#endif
