#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

#define EXIT_DIFFERENT 63
#define EXIT_SAME      0

void usage () {
    fputs("Usage: cmp <file1> <file2> <ignore whitespaces?>\n", stderr);
    fputs("       ignore whitespaces: y/n\n", stderr);
    exit(EXIT_FAILURE);
}

void check (bool cond, const char *funct) {
  if (cond) {
    perror(funct);
    exit(EXIT_FAILURE);
  }
}

void die (const char *msg) {
  fputs(msg, stderr);
  fputc('\n', stderr);
  exit(EXIT_FAILURE);
}

void different () {
  exit(EXIT_DIFFERENT);
}
void same () {
  exit(EXIT_SAME);
}

void cmp_with_ws (FILE *file1, FILE *file2) {
  int c1 = fgetc(file1);
  int c2 = fgetc(file2);
  if (c1 != c2) return different();
  if (c1 == EOF) return same();
  return cmp_with_ws(file1, file2);
}

bool is_ws (char c) {
  return c == ' ' || c == '\n' || c == '\t' || c == '\r';
}

void cmp_ignore_ws (FILE *file1, FILE *file2, bool is_in_ws) {
  int c1 = fgetc(file1);
  int c2 = fgetc(file2);
  bool c1_is_ws = is_ws(c1);
  if (c1_is_ws) c1 = EOF;
  bool c2_is_ws = is_ws(c2);
  if (c2_is_ws) c2 = EOF;
  if (c1_is_ws && c2_is_ws) return cmp_ignore_ws(file1, file2, true);
  if (is_in_ws) {
    if (c1_is_ws && !c2_is_ws) {
      ungetc(c2, file2);
      return cmp_ignore_ws(file1, file2, true);
    }
    if (!c1_is_ws && c2_is_ws) {
      ungetc(c1, file1);
      return cmp_ignore_ws(file1, file2, true);
    }
  }
  // both not ws or not in ws
  if (c1 == EOF && c2 == EOF) return same();
  if (c1 != c2) return different();
  return cmp_ignore_ws(file1, file2, false);
}

int main (int argc, char **argv) {
  if (argc != 4) usage();

  char *name1 = argv[1];
  char *name2 = argv[2];
  char ignore_ws_flag = *argv[3];
  if (ignore_ws_flag != 'y' && ignore_ws_flag != 'n') usage();
  bool ignore_ws = ignore_ws_flag == 'y';

  struct stat st1, st2;
  check(stat(name1, &st1), "stat");
  if (!S_ISREG(st1.st_mode)) die("file 1 is not regular file");
  check(stat(name2, &st2), "stat");
  if (!S_ISREG(st2.st_mode)) die("file 2 is not regular file");
  if (!ignore_ws && st1.st_size != st2.st_size) different();

  FILE *file1 = fopen(name1, "r");
  check(!file1, "fopen");
  FILE *file2 = fopen(name2, "r");
  check(!file2, "fopen");

  if (ignore_ws) cmp_ignore_ws(file1, file2, true);
  else cmp_with_ws(file1, file2);

  die("cmp has a problem");
}
