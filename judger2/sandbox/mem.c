#include <sys/resource.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void print () {
  struct rusage rusage;
  getrusage(RUSAGE_SELF, &rusage);
  printf("%ld\n", rusage.ru_maxrss * 1024);
}

#define sz 0

int main () {
  if (sz > 0) {
    char *mem = (char *) malloc(sz);
    for (int i = 0; i < sz; i += 4096) mem[i] = 1;
  }
  print();
  if (fork() == 0) {
    print();
  }
  return 0;
}
