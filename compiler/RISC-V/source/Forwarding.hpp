#pragma once
#include <iostream>

namespace sjtu {
class Forwarding {
    enum { FD_SIZE = 3 };
private:
    int32_t rd[FD_SIZE];
    uint32_t output[FD_SIZE];
    uint32_t clk[FD_SIZE];
    uint32_t rank[FD_SIZE];
    uint32_t max_rank;
public:
    Forwarding() {
        clear();
    }
    void clear() {
        for (int i = 0; i < FD_SIZE; i++)
            rd[i] = 0, rank[i] = 0;
        max_rank = 0;
    }
    bool set_change_rd(uint32_t Rd, uint32_t Clk) {
        if (!Rd) return false;
        for (int i = 0; i < FD_SIZE; i++)
            if (rd[i] == 0) {
                rd[i] = -(int)Rd;
                clk[i] = Clk;
                rank[i] = ++max_rank;
                return true;
            }
        return false;
    }
    bool set_change_output(uint32_t ALUOutput, uint32_t Clk) {
        for (int i = 0; i < FD_SIZE; i++)
            if (clk[i] == Clk) {
                rd[i] = -rd[i];
                output[i] = ALUOutput;
                return true;
            }
        return false;
    }
    bool set_complete(uint32_t Clk) {
        for (int i = 0; i < FD_SIZE; i++)
            if (clk[i] == Clk) {
                for (int j = 0; j < FD_SIZE; j++)
                    if (rank[j] > rank[i])
                        rank[j]--;
                rank[i] = 0;
                max_rank--;
                rd[i] = 0;
                return true;
            }
        return false;
    }
    bool check_changed(const uint32_t &pointer) {
        if (pointer == 0) 
            return false;
        for (int i = 0; i < FD_SIZE; i++)
            if (pointer == rd[i] or pointer == -rd[i])
                return true;
        return false;
    }
    bool check_output(const uint32_t &pointer) {
        uint32_t rnk = 0, k = 0;
        for (int i = 0; i < FD_SIZE; i++)
            if (pointer == rd[i] or pointer == -rd[i]) {
                if (rank[i] > rnk) 
                    rnk = rank[i], k = i;
            }
            if (rd[k] == pointer) 
                return true;
            else
                return false;
    }
    uint32_t get(const uint32_t &pointer) {
        uint32_t rnk = 0, k = 0;
        for (int i = 0; i < FD_SIZE; i++)
            if (pointer == rd[i] or pointer == -rd[i]) {
                if (rank[i] > rnk) 
                    rnk = rank[i], k = i;
            }
        return output[k];
    }
};
} // namespace sjtu

