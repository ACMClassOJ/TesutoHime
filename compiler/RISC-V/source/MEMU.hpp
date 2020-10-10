#pragma once

#include <iostream>
#include "StageUnit.hpp"
#include "EX_MEM.hpp"
#include "MEM_WB.hpp"
#include "RandomAccessMemory.hpp"
#include "Forwarding.hpp"
#include "InstructionDecoder.hpp"

namespace sjtu {
class MEMU : public StageUnit {
private:
    EX_MEM &ex_mem;
    MEM_WB &mem_wb;
    RandomAccessMemory &RAM;
    Forwarding &FD;
public:
    MEMU(
        EX_MEM &ex_mem, 
        MEM_WB &mem_wb, 
        RandomAccessMemory &RAM, 
        Forwarding &FD
    ) : StageUnit(), ex_mem(ex_mem), mem_wb(mem_wb), RAM(RAM), FD(FD) {}
    void start() {
        StageUnit::start();
        switch (InstructionDecoder(ex_mem.IR).getOpcode())
        {
        case OC_LOAD: case OC_STORE:
            set_clk_cyc(3); // LOAD STORE 指令需要运行三个时钟周期
            break;
        }
    }
    void run() {
        if (get_clk_cyc() == 1) end();
        else if (get_clk_cyc() > 0)
            --get_clk_cyc();
    }
    void end() {
        StageUnit::end();
        mem_wb.IR = ex_mem.IR;
        if (ex_mem.IR == NOP) return;
        mem_wb.CLK = ex_mem.CLK;

        InstructionDecoder IR(ex_mem.IR);
        switch (IR.getOpcode())
        {
        case OC_OP: case OC_OP_IMM: case OC_LUI: case OC_AUIPC: case OC_JAL: case OC_JALR:
            mem_wb.ALUOutput = ex_mem.ALUOutput;
            break;
        case OC_BRANCH:
            break;
        case OC_LOAD:
            set_clk_cyc(3); // LOAD 指令需要运行三个时钟周期
            switch (IR.getFunct3()) {
                case 0b000: mem_wb.LMD = (int)(int8_t)RAM.read(ex_mem.ALUOutput);
                    break;
                case 0b001: mem_wb.LMD = (int)(int16_t)(RAM.read(ex_mem.ALUOutput) | RAM.read(ex_mem.ALUOutput + 1) << 8);
                    break;
                case 0b010: mem_wb.LMD = RAM.read(ex_mem.ALUOutput) | RAM.read(ex_mem.ALUOutput + 1) << 8 | RAM.read(ex_mem.ALUOutput + 2) << 16 | RAM.read(ex_mem.ALUOutput + 3) << 24;
                    break;
                case 0b100: mem_wb.LMD = RAM.read(ex_mem.ALUOutput);
                    break;
                case 0b101: mem_wb.LMD = RAM.read(ex_mem.ALUOutput) | RAM.read(ex_mem.ALUOutput + 1) << 8;
                    break;
            }
            FD.set_change_output(mem_wb.LMD, ex_mem.CLK);
            break;
        case OC_STORE:
            set_clk_cyc(3); // STORE 指令需要运行三个时钟周期
            mem_wb.IR = ex_mem.IR;
            switch (IR.getFunct3()) {
                case 0b010:
                    RAM.write(ex_mem.ALUOutput + 3, ex_mem.B >> 24);
                    RAM.write(ex_mem.ALUOutput + 2, ex_mem.B >> 16);
                case 0b001:
                    RAM.write(ex_mem.ALUOutput + 1, ex_mem.B >> 8);
                case 0b000:
                    RAM.write(ex_mem.ALUOutput, ex_mem.B);
                    break;
            }
            break;
        }
        ex_mem.clear();
    }
    void restart() {
        mem_wb.clear();
        start();
    }
};

}

