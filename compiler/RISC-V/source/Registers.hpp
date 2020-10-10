#pragma once
#include <iostream>

namespace sjtu {

class Registers {
private:
    uint32_t Regs[32];
    //std::map<uint32_t, bool>R, W;
public:
    Registers() {
        Regs[0] = 0;
    }
    uint32_t read(const uint32_t &pointer) {
        //R[pointer] = true;
        return Regs[pointer];
    }
    void write(const uint32_t &pointer, const uint32_t &value) {
        if (!pointer) return;
        //W[pointer] = true;
        Regs[pointer] = value;
    }
    /*
    void print() {
        using namespace std;
        string nm[] = {
            "zero", "  ra", "  sp", "  gp", "  tp", "  t0", "  t1", "  t2",
            "  s0", "  s1", 
            "  a0", "  a1", "  a2", "  a3", "  a4", "  a5", "  a6", "  a7",
            "  s2", "  s3", "  s4", "  s5", "  s6", "  s7", "  s8", "  s9",
            " s10", " s11", "  t3", "  t4", "  t5", "  t6"
        };
        cerr << "Registers : " << endl;
        for (int i = 0; i < 8; i++) {
            cerr << "    ";
            for (int j = 0; j < 4; j++) {
                if (R[i * 4 + j] && W[i * 4 + j]) cerr << '{';
                else if (R[i * 4 + j]) cerr << '(';
                else if (W[i * 4 + j]) cerr << '[';
                else cerr << ' ';
                cerr << nm[i * 4 + j] << ':' << setw(8) << setfill('0') << hex << Regs[i * 4 + j];
                if (R[i * 4 + j] && W[i * 4 + j]) cerr << '}';
                else if (R[i * 4 + j]) cerr << ')';
                else if (W[i * 4 + j]) cerr << ']';
                else cerr << ' ';
            }
            cerr << endl;
        }
        R.clear(); W.clear();
    }
    */
};



} // namespace sjtu


