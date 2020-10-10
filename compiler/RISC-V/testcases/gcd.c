#include "io.inc"

int gcd(int x, int y) {
  if (x % y == 0)
    return y;
  else
    return gcd(y, x % y);
}

int main() {
  printInt(gcd(10, 1));
  printInt(gcd(34986, 3087));
  printInt(gcd(2907, 1539));
  return judgeResult % Mod;  // 178
}