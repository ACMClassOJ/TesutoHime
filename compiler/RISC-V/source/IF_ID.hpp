#pragma once 
#include <iostream>
#include <iomanip>
#include "Instruction.hpp"
namespace sjtu {
    struct IF_ID { 
    uint32_t IR; 
    uint32_t NPC; 
    uint32_t PPC;
    uint32_t PC; 
    uint32_t CLK;
    void clear() { IR = NOP; }
    void print() {
        using namespace std;
        cerr << "IF_ID : " << endl;
        cerr << "    " << "IR =\t" << setw(8) << setfill('0') << hex << IR << endl;
        cerr << "    " << "NPC =\t" << setw(8) << setfill('0') << hex << NPC << endl;
        cerr << "    " << "PPC =\t" << setw(8) << setfill('0') << hex << PPC << endl;
        cerr << "    " << "PC =\t" << setw(8) << setfill('0') << hex << PC << endl;
        cerr << "    " << "CLK =\t" << setw(8) << setfill('0') << hex << CLK << endl;
    }
};
} // namespace sjtu

