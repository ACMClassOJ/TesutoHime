#pragma once

namespace sjtu {

enum InstructionOperation {
    NOP, LUI, AUIPC, JAL, JALR, BEQ, BNE, BLT, BGE, BLTU, BGEU, LB, LH, LW, LBU, LHU, SB, SH, SW, ADDI, SLTI, SLTIU, XORI, ORI, ANDI, SLLI, SRLI, SRAI, ADD, SUB, SLL, SLT, SLTU, XOR, SRL, SRA, OR, AND
};
enum InstructionOpcode {
    OC_NOP     = 0b0000000,
    OC_LUI     = 0b0110111,
    OC_AUIPC   = 0b0010111,
    OC_JAL     = 0b1101111,
    OC_JALR    = 0b1100111,
    OC_BRANCH  = 0b1100011,
    OC_LOAD    = 0b0000011,
    OC_STORE   = 0b0100011,
    OC_OP_IMM  = 0b0010011,
    OC_OP      = 0b0110011
};

}

