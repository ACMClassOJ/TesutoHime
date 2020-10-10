#pragma once
#include <iostream>

namespace sjtu {
class TwoBitSaturatingCounter {
private:
    int8_t curState;
public:
    TwoBitSaturatingCounter() {
        curState = 0;
    }
    bool get() {
        return curState >> 1 & 1 ?  true : false;
    }
    void set(bool PredictResult) {
        PredictResult ? ++curState : --curState;
        if (curState < 0) curState = 0;
        if (curState > 3) curState = 3;
    }
    void print() {
        if (curState & 3 == 3)
            std::cerr << "TwoBitSaturatingCounter" << " : " << "stronglyToken" << std::endl;
        if (curState & 3 == 2)
            std::cerr << "TwoBitSaturatingCounter" << " : " << "weaklyToken" << std::endl;
        if (curState & 3 == 1)
            std::cerr << "TwoBitSaturatingCounter" << " : " << "weaklyNotToken" << std::endl;
        if (curState & 3 == 0)
            std::cerr << "TwoBitSaturatingCounter" << " : " << "stronglyNotToken" << std::endl;
    }
};

typedef TwoBitSaturatingCounter BranchPredictor;

}

