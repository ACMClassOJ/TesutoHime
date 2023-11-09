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
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* This is the worker UID inside the clone(2)'d user
   namespace. An UID map is needed to setuid(2) to this UID.
   See deploy instructions for more detail on that.
   See also: https://lwn.net/Articles/532593/
 */
#define WORKER_UID 65534
#define CHILD_DIE_STATUS 249
typedef long long time_ms_t;

inline static void check (int cond, const char *msg) {
  if (cond) {
    perror(msg);
    exit(EXIT_FAILURE);
  }
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
  if (argc < 4) {
    fprintf(stderr, "Usage: runner <time limit msecs> <result file> <executable> [args...]\n");
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
    if (setuid(WORKER_UID)) {
      die_child(pipefd[1], "setuid");
    }
    set_timer(time_limit);

    execv(argv[3], &argv[3]);
    /* execv return only on errors. */
    die_child(pipefd[1], "execv");
  }

  time_ms_t start_time = gettime();
  int status = -1;
  struct rusage rusage;
  /* Using wait4(2) here to get rusage data directly. */
  check(wait4(child_pid, &status, 0, &rusage) < 0, "wait4");
  time_ms_t end_time = gettime();
  time_ms_t real_time = end_time - start_time;

  /* maxrss is in kbytes on Linux. */
  long mem = rusage.ru_maxrss * 1024;

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

  fprintf(results, "run %d %lld %ld\n", code, real_time, mem);
  check(fclose(results), "fclose");

  return 0;
}
