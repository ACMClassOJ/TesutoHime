#pragma once

#include <iostream>
#include "StageUnit.hpp"
#include "MEM_WB.hpp"
#include "Registers.hpp"
#include "Forwarding.hpp"
#include "InstructionDecoder.hpp"

namespace sjtu {

class WBU : public StageUnit {
private:
    MEM_WB &mem_wb;
    Registers &Regs;
    Forwarding &FD;
public:
    WBU(
        MEM_WB &mem_wb, 
        Registers &Regs,
        Forwarding &FD
    ) : StageUnit(), mem_wb(mem_wb), Regs(Regs), FD(FD) {}
    void start() {
        StageUnit::start();
    }
    void run() {
        end();
    }
    void end() {
        StageUnit::end();
        if (mem_wb.IR == NOP) return;
        InstructionDecoder IR(mem_wb.IR);
        switch (IR.getOpcode())
        {
        case OC_JAL: case OC_JALR: case OC_OP: case OC_OP_IMM: case OC_LUI: case OC_AUIPC: 
            Regs.write(IR.getRd(), mem_wb.ALUOutput);
            FD.set_complete(mem_wb.CLK);
            break;
        case OC_BRANCH:
            break;
        case OC_LOAD:
            Regs.write(IR.getRd(), mem_wb.LMD);
            FD.set_complete(mem_wb.CLK);
            break;
        case OC_STORE:
            break;
        }
        mem_wb.clear();
    }
    void restart() {
        start();
    }
};
    
} // namespace sjtu

