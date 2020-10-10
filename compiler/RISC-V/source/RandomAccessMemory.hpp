#pragma once
#include <iostream>

namespace sjtu {

class RandomAccessMemory {
private:
    uint8_t * Mem;
    uint32_t size;
    //std::map<uint32_t, bool>R, W;
public:
    RandomAccessMemory(uint32_t size = 1 << 20) : size(size) {
        Mem = new uint8_t[size];
        //R.clear();
        //W.clear();
    }
    uint8_t read(const uint32_t &pointer) { 
        //R[pointer] = true;
        return Mem[pointer]; 
    }
    void write(const uint32_t &pointer, const uint8_t &value) { 
        //W[pointer] = true;
        Mem[pointer] = value; 
    }
    ~RandomAccessMemory() { delete [] Mem; }
    /*
    void print(uint32_t begin, uint32_t end) {
        using namespace std;
        cerr << "RandomAccessMemory : " << endl << setw(4) << setfill(' ') << hex << (uint16_t)begin << '\t';
        for (int i = begin; i != end; i++) {
            if (R[i] && W[i]) cerr << '{';
            else if (R[i]) cerr << '(';
            else if (W[i]) cerr << '[';
            else cerr << ' ';
            cerr << setw(2) << setfill('0') << hex << (int)Mem[i];
            if (R[Mem[i]] && W[i]) cerr << '}';
            else if (R[i]) cerr << ')';
            else if (W[i]) cerr << ']';
            else cerr << ' ';
            if ((i - begin) % 20 == 19) cerr << endl << setw(4) << setfill(' ') << hex << (uint16_t)(i + 1) << '\t';
            R[i] = W[i] = false;
        }
        cerr << endl;
    }*/
    /*
    void print_change() {
        for (auto i : R) 
            if (i.second)
                print(i.first - 10, i.first + 10);
        for (auto i : W) 
            if (i.second)
                print(i.first - 10, i.first + 10);
    }*/
};

}

