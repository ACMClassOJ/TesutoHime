#include "source/CPU.hpp"

int main() {
    sjtu::RandomAccessMemory RAM;
    sjtu::CPU cpu(RAM);
    cpu.load_program();
    cpu.run_with_pipeline();
}