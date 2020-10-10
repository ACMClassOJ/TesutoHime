#pragma once
#include <iostream>

namespace sjtu {

class ArithmeticLogicUnit {
private:
    uint32_t input1, input2; 
public:
    enum OpType {
        OT_NOP, OT_ADD, OT_SUB, OT_SLL, OT_SLT, OT_SLTU, OT_XOR, OT_SRA, OT_SRL, OT_OR, OT_AND, OT_EQ
    } opType;
    void print() {
        using namespace std;
        std::cerr << "ArithmeticLogicUnit" << " : ";
        std::cerr << input1;
        cerr << ' ';
        switch (opType) {
            case OT_NOP: cerr << "NOP"; break;
            case OT_ADD: cerr << "ADD"; break;
            case OT_SUB: cerr << "SUB"; break;
            case OT_SLL: cerr << "SLL"; break;
            case OT_SLT: cerr << "SLT"; break;
            case OT_SLTU: cerr << "SLTU"; break;
            case OT_XOR: cerr << "XOR"; break;
            case OT_SRA: cerr << "SRA"; break;
            case OT_SRL: cerr << "SRL"; break;
            case OT_OR: cerr << "OR"; break;
            case OT_AND: cerr << "AND"; break;
            case OT_EQ: cerr << "EQ"; break;
        }
        cerr << ' ';
        std::cerr << input2 << std::endl;
    }
    void setImm() {
        if (opType == OT_SUB)
            opType = OT_ADD;
    }
    void setOpType(const OpType &type) { opType = type; }
    void setOpType(const uint32_t &funct3, const uint32_t &funct7) {
        switch (funct3) {
        case 0b000: // ADD SUB
            if (funct7 == 0)
                this->opType = OT_ADD;
            else 
                this->opType = OT_SUB;
            break;
        case 0b001: // SLL
            this->opType = OT_SLL; break;
        case 0b010: // SLT
            this->opType = OT_SLT; break;
        case 0b011: // SLTU
            this->opType = OT_SLTU; break;
        case 0b100: // XOR
            this->opType = OT_XOR; break;
        case 0b101: // SRA SRL
            if (funct7 == 0)
                this->opType = OT_SRL; 
            else
                this->opType = OT_SRA; 
            break;
        case 0b110: // OR
            this->opType = OT_OR; break;
        case 0b111: // AND
            this->opType = OT_AND; break;
        default:
            this->opType = OT_NOP;  break;
        }
    }
    void setInput1(const uint32_t &value) {
        input1 = value;
    }
    void setInput2(const uint32_t &value) {
        input2 = value;
    }
    uint32_t getOutput() const {
        switch (opType) {
            case OT_NOP: return 0u; 
            case OT_ADD: return input1 + input2;
            case OT_SUB: return input1 - input2;
            case OT_SLL: return input1 << input2;
            case OT_SLT: return (int)input1 < (int)input2 ? 1 : 0;
            case OT_SLTU: return input1 < input2 ? 1 : 0;
            case OT_XOR: return input1 ^ input2;
            case OT_SRA: return (int)input1 >> input2;
            case OT_SRL: return input1 >> input2;
            case OT_OR: return input1 | input2;
            case OT_AND: return input1 & input2;
            case OT_EQ: return input1 == input2;
        }
        return 0u;
    }
};

}

