#pragma once
#include <iostream>
#include <iomanip>

namespace sjtu {
class StageUnit {
private:
    uint32_t remain_clk_cyc;
    bool hazard;
public:
    StageUnit() : remain_clk_cyc(0), hazard(false) {}
    void set_clk_cyc(uint32_t t) {
        remain_clk_cyc = t;
    } 
    uint32_t &get_clk_cyc() {
        return remain_clk_cyc;
    }
    void start() {
        remain_clk_cyc = 1;
    }
    void end() {
        remain_clk_cyc = 0;
    }
    bool is_not_finished() {
        return remain_clk_cyc;
    }
    void throw_hazard() {
        hazard = true;
    }
    bool catch_hazard() {
        return hazard;
    }
    void solve_hazard() {
        hazard = false;
    }
    void restart() {
        start();   
    }
};
   
} // namespace sjtu

