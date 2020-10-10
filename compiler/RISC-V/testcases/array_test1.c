#include "io.inc"

int a[4];
int main() {
  int b[4];
  int i;
  for (i = 0; i < 4; i++) {
    a[i] = 0;
    b[i] = i + 1;
  }
  for (i = 0; i < 4; i++) {
    printInt(a[i]);
  }

  int *p;
  p = b;
  for (i = 0; i < 4; i++) {
    printInt(p[i]);
  }
  return judgeResult % Mod; // 123
}