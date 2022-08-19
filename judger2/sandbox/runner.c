#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define WORKER_UID 65534
typedef long long time_ms_t;

void check (int cond, const char *msg) {
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
  struct itimerval val;
  val.it_value.tv_sec = time / SEC_TO_MS;
  val.it_value.tv_usec = (time % SEC_TO_MS) * MS_TO_US;
  val.it_interval.tv_sec = 0;
  val.it_interval.tv_usec = 10 * MS_TO_US;
  check(setitimer(ITIMER_REAL, &val, NULL), "setitimer");
}

int main (int argc, char **argv) {
  if (argc < 4) {
    fprintf(stderr, "Usage: runner <time limit msecs> <result file> <executable> [args...]\n");
    exit(126);
  }
  if (getuid() != 0 || geteuid() != 0) {
    fprintf(stderr, "runner needs to be run as root\n");
    exit(EXIT_FAILURE);
  }

  time_ms_t time_limit = atoll(argv[1]);
  const char * const results_file = argv[2];
  FILE *results = fopen(results_file, "w");
  check(!results, "fopen");
  check(chmod(results_file, 0600), "chmod");

  pid_t child_pid = fork();
  check(child_pid < 0, "fork");
  if (child_pid == 0) { // is child
    check(fclose(results), "fclose");
    check(setuid(WORKER_UID), "setuid");
    set_timer(time_limit);

    check(execv(argv[3], &argv[3]), "execv");
    // execv returns only on errors.
  }

  time_ms_t start_time = gettime();
  int status = -1;
  struct rusage rusage;
  check(wait4(child_pid, &status, 0, &rusage) < 0, "wait4");
  time_ms_t end_time = gettime();
  time_ms_t real_time = end_time - start_time;

  long mem = rusage.ru_maxrss * 1024;

  int code;
  if (WIFEXITED(status)) {
    code = WEXITSTATUS(status);
  } else if (WIFSIGNALED(status) || WIFSTOPPED(status)) {
    code = 256 + WTERMSIG(status);
  } else {
    code = -1;
  }

  fprintf(results, "run %d %lld %ld\n", code, real_time, mem);
  check(fclose(results), "fclose");

  return 0;
}
