#include "io.inc"

int main() {
  int a[100][100];
  int i;
  int j;
  int sum = 0;

  for (i = 0; i < 100; i++)
    for (j = 0; j < 100; j++)
      a[i][j] = 0;
  int quotient;
  int remainder;
  for (i = 0; i < 100; i++)
    if (i > 20 && i < 80) {
      for (j = 0; j < 100; j++)
        if (j > 5 || i < 90) {
          quotient = j * 4 / 100;
          remainder = j * 4 % 100;
          a[i + quotient][remainder] = j + (100 - 1 + 1 - 1 + 1) / 2;
        }
    }

  for (i = 0; i < 100; i++)
    for (j = 0; j < 100; j++)
      sum = sum + a[i][j];
  printInt(sum);
  return judgeResult % Mod;  // 88
}
