#pragma once

#include <iostream>
#include "StageUnit.hpp"
#include "ID_EX.hpp"
#include "EX_MEM.hpp"
#include "BranchPredictor.hpp"
#include "Forwarding.hpp"
#include "ArithmeticLogicUnit.hpp"
#include "InstructionDecoder.hpp"

namespace sjtu {
class EXU : public StageUnit {
private:
    uint32_t &pc;
    ID_EX &id_ex;
    EX_MEM &ex_mem;
    BranchPredictor &BP;
    Forwarding &FD;
    ArithmeticLogicUnit ALU;
public:
    EXU(
        uint32_t &pc, 
        ID_EX &id_ex, 
        EX_MEM &ex_mem, 
        BranchPredictor &BP, 
        Forwarding &FD
    ) : StageUnit(), pc(pc), id_ex(id_ex), ex_mem(ex_mem), BP(BP), FD(FD) {}
    void start() {
        StageUnit::start();
    }
    void run() {
        end();
    }
    void end() {
        StageUnit::end();
        ex_mem.IR = id_ex.IR;
        if (id_ex.IR == NOP) return;
        ex_mem.CLK = id_ex.CLK;
        InstructionDecoder IR(id_ex.IR);
        
        if (IR.checkRd())
            FD.set_change_rd(IR.getRd(), id_ex.CLK);

        switch (IR.getOpcode())
        {
        case OC_OP_IMM: 
            ALU.setInput1(id_ex.A);
            ALU.setInput2(id_ex.B);
            ALU.setOpType(IR.getFunct3(), IR.getFunct7());
            ALU.setImm();
            ex_mem.ALUOutput = ALU.getOutput(); 
            FD.set_change_output(ex_mem.ALUOutput, id_ex.CLK);
            break;
        case OC_OP: 
            ALU.setInput1(id_ex.A);
            ALU.setInput2(id_ex.B);
            ALU.setOpType(IR.getFunct3(), IR.getFunct7());
            ex_mem.ALUOutput = ALU.getOutput(); 
            FD.set_change_output(ex_mem.ALUOutput, id_ex.CLK);
            break;
        case OC_LUI: 
            ex_mem.ALUOutput = id_ex.B;
            FD.set_change_output(ex_mem.ALUOutput, id_ex.CLK);
            break;
        case OC_AUIPC: 
            ALU.setInput1(id_ex.B);
            ALU.setInput2(id_ex.PC);
            ALU.setOpType(ArithmeticLogicUnit::OT_ADD);
            ex_mem.ALUOutput = ALU.getOutput();
            FD.set_change_output(ex_mem.ALUOutput, id_ex.CLK);
            break;
        case OC_JAL: case OC_JALR:
            ALU.setInput1(id_ex.PC);
            ALU.setInput2(4);
            ALU.setOpType(ArithmeticLogicUnit::OT_ADD);
            ex_mem.ALUOutput = ALU.getOutput();
            FD.set_change_output(ex_mem.ALUOutput, id_ex.CLK);
            break;
        case OC_BRANCH: {
            bool token;
            uint32_t operation = IR.getOperation();
            switch (operation) {
                case BEQ: case BNE: 
                    ALU.setOpType(ArithmeticLogicUnit::OT_EQ);
                    ALU.setInput1(id_ex.A);
                    ALU.setInput2(id_ex.B);
                    token = ALU.getOutput();
                    break; 
                case BLT: case BGE:
                    ALU.setInput1(id_ex.A);
                    ALU.setInput2(id_ex.B);
                    ALU.setOpType(ArithmeticLogicUnit::OT_SLT);
                    token = ALU.getOutput();
                    break;
                case BLTU: case BGEU:
                    ALU.setInput1(id_ex.A);
                    ALU.setInput2(id_ex.B);
                    ALU.setOpType(ArithmeticLogicUnit::OT_SLTU);
                    token = ALU.getOutput();
                    break;
            }
            if (operation == BNE or operation == BGE or operation == BGEU) 
                token = not token;
            BP.set(token);
            if (token) {
                ALU.setInput1(id_ex.PC);
                ALU.setInput2(IR.getImm());
                ALU.setOpType(ArithmeticLogicUnit::OT_ADD);
                id_ex.NPC = ALU.getOutput();
            } else {
                ALU.setInput1(id_ex.PC);
                ALU.setInput2(4);
                ALU.setOpType(ArithmeticLogicUnit::OT_ADD);
                id_ex.NPC = ALU.getOutput();
            }
            if (id_ex.PPC != id_ex.NPC) {
                pc = id_ex.NPC;
                this->throw_hazard();
                //return;
            }
        }
            break;
        case OC_LOAD: 
            ALU.setInput1(id_ex.A);
            ALU.setInput2(id_ex.B);
            ALU.setOpType(ArithmeticLogicUnit::OT_ADD);
            ex_mem.ALUOutput = ALU.getOutput();
            break;
        case OC_STORE:
            ALU.setInput1(id_ex.A);
            ALU.setInput2(IR.getImm());
            ALU.setOpType(ArithmeticLogicUnit::OT_ADD);
            ex_mem.ALUOutput = ALU.getOutput();
            ex_mem.B = id_ex.B;
            break;
        }
        
        id_ex.clear();
    }
    void restart() {
        ex_mem.clear();
        start();
    }
};    
} // namespace sjtu


