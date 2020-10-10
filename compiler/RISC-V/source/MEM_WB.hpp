#pragma once
#include <iostream>
#include <iomanip>
#include "Instruction.hpp"

namespace sjtu {
struct MEM_WB { 
    uint32_t IR; 
    uint32_t ALUOutput; 
    uint32_t LMD;
    uint32_t CLK; 
    void clear() { IR = NOP; }
    void print() {
        using namespace std;
        cerr << "MEM_WB : " << endl;
        cerr << "    " << "IR = \t" << setw(8) << setfill('0') << hex << IR << endl;
        cerr << "    " << "CLK = \t" << setw(8) << setfill('0') << hex << CLK << endl;
        cerr << "    " << "ALUOutput = \t" << setw(8) << setfill('0') << hex << ALUOutput << endl;
        cerr << "    " << "LMD = \t" << setw(8) << setfill('0') << hex << LMD << endl;
    }
};

} // namespace sjtu


