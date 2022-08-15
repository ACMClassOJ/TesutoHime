#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/stat.h>
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

time_ms_t gettime () {
  struct timespec ts;
  check(clock_gettime(CLOCK_REALTIME, &ts), "clock_gettime");
  time_ms_t time = ts.tv_sec * 1000;
  time += ts.tv_nsec / 1000000;
  return time;
}

int main (int argc, char **argv) {
  if (argc < 3) {
    fprintf(stderr, "Usage: runner <result file> <executable> [args...]\n");
    exit(126);
  }
  if (getuid() != 0 || geteuid() != 0) {
    fprintf(stderr, "runner needs to be run as root\n");
    exit(EXIT_FAILURE);
  }

  const char * const results_file = argv[1];
  FILE *results = fopen(results_file, "w");
  check(!results, "fopen");
  check(chmod(results_file, 0600), "chmod");

  pid_t child_pid = fork();
  check(child_pid < 0, "fork");
  if (child_pid == 0) { // is child
    check(fclose(results), "fclose");
    check(setuid(WORKER_UID), "setuid");

    check(execv(argv[2], &argv[2]), "execv");
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
