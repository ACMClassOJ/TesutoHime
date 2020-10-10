#include "io.inc"

int a[4];
int *pa = a;
int main() {
  int *pb[4];
  int i;
  pb[0] = pa;
  pb[1] = pa;
  pb[2] = pa;
  pb[3] = pa;
  printInt(4);
  for (i = 0; i < 4; i++)
    pb[0][i] = i + 1;
  for (i = 0; i < 4; i++)
    printInt(pb[1][i]);

  for (i = 0; i < 4; i++)
    pb[2][i] = 0;
  for (i = 0; i < 4; i++)
    printInt(pb[3][i]);
  return judgeResult % Mod;  // 43
}
