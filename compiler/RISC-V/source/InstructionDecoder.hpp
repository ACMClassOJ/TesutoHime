#pragma once
#include <iostream>
#include "Instruction.hpp"

namespace sjtu {

class InstructionDecoder {
private:
    const uint32_t &IR;
    uint32_t opcode;
    inline uint32_t substr_of_inst(const uint32_t &low, const uint32_t &len) const {
        return IR >> low & len;
    }
    inline uint32_t substr_of_inst(const uint32_t &pos) const {
        return IR >> pos & 1u;
    }
    uint32_t sign_extend(uint32_t low) {
        uint32_t rst = 0u, sign = substr_of_inst(31) << low;
        if (!sign) return 0;
        while (low < 32u) 
            rst |= sign, low++, sign <<= 1;
        return rst;
    }
    enum InstructionFormat {
        R_type, I_type, S_type, B_type, U_type, J_type
    };
    InstructionFormat getFormat() {
        switch (opcode) {
            case 0b0110111: case 0b0010111: 
                return U_type;
            case 0b1101111:
                return J_type;
            case 0b1100111:
                return I_type;
            case 0b1100011:
                return B_type;
            case 0b0000011:
                return I_type;
            case 0b0100011:
                return S_type;
            case 0b0010011: {
                uint32_t funct3 = substr_of_inst(12, 0b111);
                if (funct3 != 0b001 and funct3 != 0b101)
                    return I_type;
                else 
                    return R_type;
            }
            case 0b0110011:
                return R_type;
        }
    }
public:
    void print() {
        using namespace std;
        cerr << "InstructionDecoder : " << endl;
        cerr << hex << IR << ' ';
        switch (getOperation()) {
            case NOP: cerr << "NOP"; break;
            case LUI: cerr << "LUI"; break;
            case AUIPC: cerr << "AUIPC"; break;
            case JAL: cerr << "JAL"; break;
            case JALR: cerr << "JALR"; break;
            case BEQ: cerr << "BEQ"; break;
            case BNE: cerr << "BNE"; break;
            case BLT: cerr << "BLT"; break;
            case BGE: cerr << "BGE"; break;
            case BLTU: cerr << "BLTU"; break;
            case BGEU: cerr << "BGEU"; break;
            case LB: cerr << "LB"; break;
            case LH: cerr << "LH"; break;
            case LW: cerr << "LW"; break;
            case LBU: cerr << "LBU"; break;
            case LHU: cerr << "LHU"; break;
            case SB: cerr << "SB"; break;
            case SH: cerr << "SH"; break;
            case SW: cerr << "SW"; break;
            case ADDI: cerr << "ADDI"; break;
            case SLTI: cerr << "SLTI"; break;
            case SLTIU: cerr << "SLTIU"; break;
            case XORI: cerr << "XORI"; break;
            case ORI: cerr << "ORI"; break;
            case ANDI: cerr << "ANDI"; break;
            case SLLI: cerr << "SLLI"; break;
            case SRLI: cerr << "SRLI"; break;
            case SRAI: cerr << "SRAI"; break;
            case ADD: cerr << "ADD"; break;
            case SUB: cerr << "SUB"; break;
            case SLL: cerr << "SLL"; break;
            case SLT: cerr << "SLT"; break;
            case SLTU: cerr << "SLTU"; break;
            case XOR: cerr << "XOR"; break;
            case SRL: cerr << "SRL"; break;
            case SRA: cerr << "SRA"; break;
            case OR: cerr << "OR"; break;
            case AND: cerr << "AND"; break;
        }
        if (checkRd()) 
            switch (getRd()) {
                case 0: cerr << "zero";
                case 1: cerr << "zero";
                case 2: cerr << "zero";
                case 3: cerr << "zero";
                case 4: cerr << "zero";
                case 5: cerr << "zero";
            }
        cerr << endl;
    }
    InstructionDecoder(const uint32_t &IR) : IR(IR) {
        opcode = substr_of_inst(0, 0b1111111);
    }
    bool checkRd() {
        return opcode != OC_BRANCH and opcode != OC_STORE;
    }
    bool checkRs1() {
        return opcode != OC_LUI and opcode != OC_AUIPC and opcode != OC_JAL;
    }
    bool checkRs2() {
        return checkRs1() and opcode != OC_LOAD and opcode != OC_OP_IMM;
    }
    bool checkShamt() {
        return opcode == OC_OP_IMM and (getFunct3() == 0b001 or getFunct3() == 0b101);
    }
    uint32_t getOpcode()    { return opcode; }
    uint32_t getRd()        { return substr_of_inst(7, 0b11111); }
    uint32_t getFunct3()    { return substr_of_inst(12, 0b111); }
    uint32_t getRs1()       { return substr_of_inst(15, 0b11111); }
    uint32_t getRs2()       { return substr_of_inst(20, 0b11111); }
    uint32_t getShamt()     { return substr_of_inst(20, 0b11111); }
    uint32_t getFunct7()    { return substr_of_inst(25, 0b1111111); }
    uint32_t getImm() {
        switch (getFormat()) {
            case R_type: return 0u;
            case I_type: 
                return (substr_of_inst(20, 0b111111111111) | sign_extend(11)); 
            case S_type: 
                return (substr_of_inst(25, 0b1111111) << 5 | substr_of_inst(7, 0b11111) | sign_extend(11));
            case B_type: 
                return (substr_of_inst(25, 0b111111) << 5 | substr_of_inst(8, 0b1111) << 1 | substr_of_inst(7) << 11 | sign_extend(12));
            case U_type:
                return (substr_of_inst(12, 0b11111111111111111111) << 12 | sign_extend(31));
            case J_type:
                return (substr_of_inst(21, 0b1111111111) << 1 | substr_of_inst(20) << 11 | substr_of_inst(12, 0b11111111) << 12 | sign_extend(20));
        }
    }
    InstructionOperation getOperation() {
        uint32_t funct3 = getFunct3();
        uint32_t funct7 = getFunct7();

        switch (opcode) {
            default: return NOP;
            case 0b0110111: return LUI;
            case 0b0010111: return AUIPC;
            case 0b1101111: return JAL;
            case 0b1100111: return JALR;
            case 0b1100011: 
                switch (funct3) {
                    case 0b000: return BEQ; //BEQ
                    case 0b001: return BNE; //BNE
                    case 0b100: return BLT; //BLT
                    case 0b101: return BGE; //BGE
                    case 0b110: return BLTU; //BLTU
                    case 0b111: return BGEU; //BGEU
                    default: return NOP;
                }
                break;
            case 0b0000011:
                switch (funct3) {
                    case 0b000: return LB;  //LB
                    case 0b001: return LH;  //LH
                    case 0b010: return LW;  //LW
                    case 0b100: return LBU; //LBU
                    case 0b101: return LHU; //LHU
                    default: return NOP;
                }
            case 0b0100011:
                switch (funct3) {
                    case 0b000: return SB; //SB
                    case 0b001: return SH; //SH
                    case 0b010: return SW; //SW
                    default: return NOP;
                }
            case 0b0010011:
                if (funct3 != 0b001 and funct3 != 0b101) {
                    switch (funct3) {
                        case 0b000: return ADDI;    //ADDI
                        case 0b010: return SLTI;    //SLTI
                        case 0b011: return SLTIU;   //SLTIU
                        case 0b100: return XORI;    //XORI
                        case 0b110: return ORI;     //ORI
                        case 0b111: return ANDI;    //ANDI
                        default: return NOP;
                    }
                } else {
                    if (funct3 == 0b001)
                        return SLLI; //SLLI
                    else if (funct7 == 0) 
                        return SRLI; //SRLI
                    else 
                        return SRAI; //SRAI
                }
                break;
            case 0b0110011:
                switch (funct3) {
                    case 0b000: return ADDI;   
                        if (funct7 == 0)
                            return ADD; // ADD
                        else 
                            return SUB; //SUB
                        break;         
                    case 0b001: return SLL;     //SLL
                    case 0b010: return SLT;     //SLT
                    case 0b011: return SLTU;    //SLTU
                    case 0b100: return XOR;     //XOR
                    case 0b101: 
                        if (funct7 == 0)
                            return SRL; //SRL
                        else
                            return SRA; //SRA
                        break; 
                    case 0b110: return OR;      //OR
                    case 0b111: return AND;     //AND
                    default: return NOP;
                }
        }
    }  
};


}

