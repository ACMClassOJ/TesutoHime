#pragma once
#include <iostream>
#include "StageUnit.hpp"
#include "IF_ID.hpp"
#include "ID_EX.hpp"
#include "Registers.hpp"
#include "BranchPredictor.hpp"
#include "AdderUnit.hpp"
#include "Forwarding.hpp"
#include "InstructionDecoder.hpp"

namespace sjtu {    
class IDU : public StageUnit {
private:
    uint32_t &pc;
    IF_ID &if_id;
    ID_EX &id_ex;
    Registers &Regs;
    BranchPredictor &BP;
    Forwarding &FD;
    AdderUnit AU;
public:
    IDU(uint32_t &pc, IF_ID &if_id, ID_EX &id_ex, Registers &Regs, BranchPredictor &BP, Forwarding &FD) : 
    StageUnit(), pc(pc), if_id(if_id), id_ex(id_ex), Regs(Regs), BP(BP), FD(FD) {}
    void start() {
        StageUnit::start();
    }
    void run() {
        end();
    }
    void end() {
        StageUnit::end();
        id_ex.IR = if_id.IR;
        if (if_id.IR == NOP) return;

        InstructionDecoder IR(if_id.IR);
        if (IR.checkRs1()) {
            if (FD.check_changed(IR.getRs1())) {
                if (FD.check_output(IR.getRs1()))
                    id_ex.A = FD.get(IR.getRs1());
                else {
                    this->throw_hazard();
                    return;
                }
            }
            else 
                id_ex.A = Regs.read(IR.getRs1());
        }
            
        if (IR.checkRs2()) {
            if (FD.check_changed(IR.getRs2())) {
                if (FD.check_output(IR.getRs2()))
                    id_ex.B = FD.get(IR.getRs2());
                else {
                    this->throw_hazard();
                    return;
                }
            }
            else 
                id_ex.B = Regs.read(IR.getRs2());
        } else if (IR.checkShamt())
            id_ex.B = IR.getShamt();
        else
            id_ex.B = IR.getImm();

        if (IR.getOpcode() == OC_JALR) {
            AU.setInput1(id_ex.A);
            AU.setInput2(IR.getImm());
            pc = AU.getOutput() & ~1u;
        }
        id_ex.CLK = if_id.CLK;
        id_ex.PC = if_id.PC;
        id_ex.NPC = if_id.NPC;
        id_ex.PPC = if_id.PPC;
        if_id.clear();
    }
    void restart() {
        id_ex.clear();
        start();
    }
};

} // namespace sjtu

