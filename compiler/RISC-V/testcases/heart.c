#include "io.inc"

char *symbol[] = {".", ":", "-", "=", "+", "*", "#", "%", "@"};


float f(float x, float y, float z) {
    float a = x * x + 9.0f / 4.0f * y * y + z * z - 1;
    return a * a * a - x * x * z * z * z - 9.0f / 80.0f * y * y * z * z * z;
}

float h(float x, float z) {
    for (float y = 1.0f; y >= 0.0f; y -= 0.001f)
        if (f(x, y, z) <= 0.0f)
            return y;
    return 0.0f;
}

float mysqrt(float x) {
  if (x == 0) return 0;
  int i;
  double v = x / 2;
  for (i = 0; i < 50; ++i)
    v = (v + x / v)/2;
  
  return v;
}

int main() {
    for (float z = 1.5f; z > -1.5f; z -= 0.05f) {
        for (float x = -1.5f; x < 1.5f; x += 0.025f) {
            float v = f(x, 0.0f, z);
            if (v <= 0.0f) {
                float y0 = h(x, z);
                float ny = 0.01f;
                float nx = h(x + ny, z) - y0;
                float nz = h(x, z + ny) - y0;
                float nd = 1.0f / mysqrt(nx * nx + ny * ny + nz * nz);
                float d = (nx + ny - nz) * nd * 0.5f + 0.5f;
                int index = (int)(d * 5.0f);
                printStr(symbol[index]);
            }
            else {
                printStr("_");
            }
        }
        printStr("\n");
    }
    return judgeResult; // 127
}
