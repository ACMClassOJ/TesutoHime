/*
 * runner.c - Program runner for ACM Class Online Judge
 * Part of TesutoHime, the ACM Class Online Judge.
 *
 * Note: This program is written in pure C (instead of C++)
 *       for minimum overhead.
 * Note: This program runs only on Linux.
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/vfs.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include "pty_seccomp.h"

/* This is the worker UID inside the clone(2)'d user
   namespace. An UID map is needed to setuid(2) to this UID.
   See deploy instructions for more detail on that.
   See also: https://lwn.net/Articles/532593/
 */
#define WORKER_UID 65534
#define CHILD_DIE_STATUS 249
#define CGROUP_PROCS_FD 3 /* Must match RunCgroup.procs_fd. */
typedef long long time_ms_t;

inline static void check (int cond, const char *msg) {
  if (cond) {
    perror(msg);
    exit(EXIT_FAILURE);
  }
}

/* Run on the host, after exec has replaced the Python daemon's address space.
 * Keep the supervisors outside the measured group. Open the membership handle
 * here so its credentials and cgroup namespace allow the sandboxed child to
 * join, including on hosts mounted with nsdelegate. Never pass it to user code.
 * Python owns cleanup, including when this setup fails before exec.
 */
static void write_cgroup(int dirfd, const char *name, const char *value) {
  int fd = openat(dirfd, name, O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
  check(fd < 0, name);
  ssize_t written;
  do {
    written = write(fd, value, strlen(value));
  } while (written < 0 && errno == EINTR);
  check(written != (ssize_t)strlen(value), name);
  check(close(fd), "close cgroup control");
}

static void require_cgroup_file(int dirfd, const char *name, int flags) {
  int fd = openat(dirfd, name, flags | O_CLOEXEC | O_NOFOLLOW);
  check(fd < 0, name);
  check(close(fd), "close cgroup control");
}

static void prepare_cgroup(int argc, char **argv) {
  if (argc < 8 || strcmp(argv[6], "--")) {
    fprintf(stderr, "Usage: runner --prepare-cgroup <parent> <acmoj-name> <memory bytes> <pids> -- <launcher> [args...]\n");
    exit(126);
  }
  int parent = open(argv[2], O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
  check(parent < 0, "open delegated cgroup");
  struct statfs fs;
  check(fstatfs(parent, &fs), "stat cgroup filesystem");
  if (fs.f_type != CGROUP2_SUPER_MAGIC) {
    fprintf(stderr, "Delegated path must be a cgroup v2 filesystem\n");
    exit(126);
  }
  write_cgroup(parent, "cgroup.subtree_control", "+memory +pids");
  check(mkdirat(parent, argv[3], 0700), "create submission cgroup");
  int group = openat(parent, argv[3], O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
  check(group < 0, "open submission cgroup");
  require_cgroup_file(group, "memory.peak", O_RDONLY);
  require_cgroup_file(group, "cgroup.kill", O_WRONLY);
  write_cgroup(group, "memory.max", argv[4]);
  write_cgroup(group, "memory.swap.max", "0");
  write_cgroup(group, "memory.oom.group", "1");
  write_cgroup(group, "pids.max", argv[5]);
  int procs = openat(group, "cgroup.procs", O_WRONLY | O_CLOEXEC | O_NOFOLLOW);
  check(procs < 0, "open cgroup.procs");
  check(close(group), "close submission cgroup");
  check(close(parent), "close cgroup parent fd");
  if (procs != CGROUP_PROCS_FD) {
    check(dup2(procs, CGROUP_PROCS_FD) < 0, "pass cgroup.procs");
    check(close(procs), "close cgroup.procs");
  } else {
    check(fcntl(procs, F_SETFD, 0), "pass cgroup.procs");
  }
  execv(argv[7], &argv[7]);
  check(1, "exec sandbox launcher");
}

#define SEC_TO_MS 1000
#define MS_TO_US  1000
#define MS_TO_NS  1000000

time_ms_t gettime () {
  struct timespec ts;
  check(clock_gettime(CLOCK_REALTIME, &ts), "clock_gettime");
  time_ms_t time = ts.tv_sec * SEC_TO_MS;
  time += ts.tv_nsec / MS_TO_NS;
  return time;
}

void set_timer (time_ms_t time) {
  /* Not using timer_create(2) here since timers created
     that way would be cleared upon execve(2), which is not
     desired for us.
   */
  struct itimerval val;
  val.it_value.tv_sec = time / SEC_TO_MS;
  val.it_value.tv_usec = (time % SEC_TO_MS) * MS_TO_US;
  val.it_interval.tv_sec = 0;
  val.it_interval.tv_usec = 10 * MS_TO_US;
  check(setitimer(ITIMER_REAL, &val, NULL), "setitimer");
}

/* send error information to parent */
inline static void die_child (int fd, const char *msg) {
  perror(msg);
  int errnum = errno;
  if (write(fd, &errnum, sizeof(errnum)) <= 0) {
    perror("write");
  }
  exit(CHILD_DIE_STATUS);
}

int main (int argc, char **argv) {
  if (argc > 1 && strcmp(argv[1], "--prepare-cgroup") == 0) {
    prepare_cgroup(argc, argv);
  }
  if (argc < 4) {
    fprintf(stderr, "Usage: runner <time limit msecs> <result file> [--pty] <executable> [args...]\n");
    exit(126);
  }
  if (getuid() != 0 || geteuid() != 0) {
    /* What we actually want is CAP_SETUID, but let's
       assume we want root.
     */
    fprintf(stderr, "runner needs to be run as root\n");
    exit(EXIT_FAILURE);
  }

  time_ms_t time_limit = atoll(argv[1]);
  const char * const results_file = argv[2];
  int use_pty = 0;
  int exec_index = 3;
  if (strcmp(argv[exec_index], "--pty") == 0) {
    use_pty = 1;
    exec_index++;
  }
  check(argc <= exec_index, "missing executable");
  check(fcntl(CGROUP_PROCS_FD, F_SETFD, FD_CLOEXEC), "protect cgroup.procs fd");
  FILE *results = fopen(results_file, "w");
  check(!results, "fopen");
  check(chmod(results_file, 0600), "chmod");

  int pipefd[2];
  check(pipe2(pipefd, O_NONBLOCK | O_CLOEXEC), "pipe");

  pid_t child_pid = fork();
  check(child_pid < 0, "fork");
  if (child_pid == 0) { /* is child */
    if (fclose(results)) {
      die_child(pipefd[1], "fclose");
    }
    ssize_t written;
    do {
      written = write(CGROUP_PROCS_FD, "0", 1);
    } while (written < 0 && errno == EINTR);
    if (written != 1) die_child(pipefd[1], "join submission cgroup");
    if (close(CGROUP_PROCS_FD)) die_child(pipefd[1], "close cgroup.procs");
    if (setuid(WORKER_UID)) {
      die_child(pipefd[1], "setuid");
    }
    if (use_pty && install_pty_seccomp()) {
      die_child(pipefd[1], "install_pty_seccomp");
    }
    set_timer(time_limit);

    execv(argv[exec_index], &argv[exec_index]);
    /* execv return only on errors. */
    die_child(pipefd[1], "execv");
  }
  check(close(CGROUP_PROCS_FD), "close supervisor cgroup.procs");

  time_ms_t start_time = gettime();
  int status = -1;
  check(waitpid(child_pid, &status, 0) < 0, "waitpid");
  time_ms_t end_time = gettime();
  time_ms_t real_time = end_time - start_time;

  int code;
  if (WIFEXITED(status)) {
    code = WEXITSTATUS(status);
  } else if (WIFSIGNALED(status) || WIFSTOPPED(status)) {
    code = 256 + WTERMSIG(status);
  } else {
    code = -1;
  }

  if (code == CHILD_DIE_STATUS) {
    int errnum;
    if (read(pipefd[0], &errnum, sizeof(errnum)) > 0) {
      code = 512 + errnum;
    }
  }

  fprintf(results, "run %d %lld\n", code, real_time);
  check(fclose(results), "fclose");

  return 0;
}
