#pragma once
#include <iostream>
#include "StageUnit.hpp"
#include "IF_ID.hpp"
#include "RandomAccessMemory.hpp"
#include "BranchPredictor.hpp"
#include "AdderUnit.hpp"
#include "InstructionDecoder.hpp"

namespace sjtu {

class IFU : public StageUnit {
private:
    uint32_t &pc;
    IF_ID &if_id;
    RandomAccessMemory &RAM;
    BranchPredictor &BP;
    AdderUnit AU;
    uint32_t clk;
public:
    IFU(uint32_t &pc, IF_ID &if_id, RandomAccessMemory &RAM, BranchPredictor &BP) : 
    StageUnit(), pc(pc), if_id(if_id), RAM(RAM), BP(BP) {}
    void start(uint32_t clk) {
        StageUnit::start();
        this->clk = clk;
    }
    void run() {
        end();
    }
    void end() {
        StageUnit::end();
        if_id.PC = pc;
        if_id.IR = 
            RAM.read(pc) | 
            RAM.read(pc + 1) << 8 | 
            RAM.read(pc + 2) << 16 | 
            RAM.read(pc + 3) << 24;
       
        InstructionDecoder IR(if_id.IR);
        AU.setInput1(pc);
        switch (IR.getOpcode()) {
            case OC_JAL:    AU.setInput2(IR.getImm());
                break;
            case OC_JALR:   AU.setInput2(4);
                break;
            case OC_BRANCH: BP.get() ? 
                            AU.setInput2(IR.getImm()) : 
                            AU.setInput2(4); 
                break;
            default:        AU.setInput2(4); 
                break;
        }
        pc = AU.getOutput();
        if_id.PPC = if_id.NPC = pc;
        if_id.CLK = clk;
    }
    void restart() {
        if_id.clear();
        StageUnit::start();
    }
};

}

