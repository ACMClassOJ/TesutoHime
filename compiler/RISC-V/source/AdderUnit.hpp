#pragma once
#include <iostream>

namespace sjtu {

class AdderUnit {
private:
    uint32_t input1, input2;
public:
    void setInput1(uint32_t value) { input1 = value; }
    void setInput2(uint32_t value) { input2 = value; }
    uint32_t getOutput() { return input1 + input2; }
    void print() {
        std::cerr << "AdderUnit : " << input1 << " + " << input2 << std::endl;
    }
};

} // namespace sjtu


