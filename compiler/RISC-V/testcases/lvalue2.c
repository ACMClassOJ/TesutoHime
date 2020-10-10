#include "io.inc"
int a[4];
int main() {
  int b[4];
  b[2] = 2;
  int *p;
  p = b;
  printInt(p[2]);
  return judgeResult % Mod;  // 175
}
