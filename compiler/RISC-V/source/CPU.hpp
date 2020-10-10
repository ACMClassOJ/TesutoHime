#pragma once

#include "BranchPredictor.hpp"
#include "ArithmeticLogicUnit.hpp"
#include "RandomAccessMemory.hpp"
#include "Registers.hpp"
#include "Forwarding.hpp"

#include "IF_ID.hpp"
#include "ID_EX.hpp"
#include "EX_MEM.hpp"
#include "MEM_WB.hpp"

#include "IFU.hpp"
#include "IDU.hpp"
#include "EXU.hpp"
#include "MEMU.hpp"
#include "WBU.hpp"

namespace sjtu{

class CPU {
private:
    //RandomAccessMemory &IM, &DM;
    RandomAccessMemory &RAM;
    Registers RegisterFile;
    IF_ID if_id;
    ID_EX id_ex;
    EX_MEM ex_mem;
    MEM_WB mem_wb;
    BranchPredictor BP;
    Forwarding FD;
    uint32_t pc = 0;
    uint32_t clk = 0;
    int to_hex(char c) {
        if (c >= '0' && c <= '9')
            return c - '0';
        if (c >= 'a' && c <= 'f')
            return c - 'a' + 10;
        if (c >= 'A' && c <= 'F')
            return c - 'A' + 10;
        return EOF;
    }
public:
    //CPU(RandomAccessMemory &IM, RandomAccessMemory &DM) : IM(IM), DM(DM) {}
    CPU(RandomAccessMemory &RAM) : RAM(RAM) {}
    void load_program() {
        char c = getchar();
        uint32_t now_ptr = 0;
        while (true) {
            if (c == EOF) {
                break;
            } else if (!isgraph(c)) {
                c = getchar();
                continue;
            } else if (c == '@') {
                now_ptr = 0;
                c = getchar();
                for (int k = 0; k < 8; k++)
                    now_ptr = now_ptr << 4 | to_hex(c), c = getchar();
                c = getchar();
            } else {
                //IM.write(now_ptr, to_hex(c) << 4 | to_hex(getchar()));
                RAM.write(now_ptr, to_hex(c) << 4 | to_hex(getchar()));
                now_ptr++;
                c = getchar();
                c = getchar();
            } 
            //if (now_ptr < 200)
            //    RAM.print(0, 200);
        }
        //RAM.print(0, 5000);
    }
    void pipline_flush() {
        if_id.clear();
        id_ex.clear();
    }
    /*
    void print() {
        using namespace std;
        cerr << "=============================" << endl;
        cerr << "PC : \t" << setw(8) << setfill('0') << hex << pc << endl;
        cerr << "CLK : \t" << setw(8) << setfill('0') << hex << clk << endl;
        if_id.print();
        id_ex.print();
        ex_mem.print();
        mem_wb.print();
        RegisterFile.print();
        //RAM.print(1 << 17, 200);
        RAM.print_change();
    }
    */
    void run_with_pipeline() {
        bool rst = false;
        if_id.clear();
        id_ex.clear();
        ex_mem.clear();
        mem_wb.clear();
        IFU IF(pc, if_id,           RAM,            BP      );
        IDU ID(pc, if_id, id_ex,    RegisterFile,   BP, FD  );
        EXU EX(pc, id_ex, ex_mem,                   BP, FD  );
        MEMU MEM(ex_mem, mem_wb,    RAM,                FD  );
        WBU WB(mem_wb,              RegisterFile,       FD  );
        while (!rst or mem_wb.IR != NOP) {
            clk++;
            //if (clk > 100) break;
            //print();
            WB.run();            
            if (WB.is_not_finished()) continue;
            else if (WB.catch_hazard()) {
                WB.solve_hazard(); 
                //WB.restart();
                continue;
            } else WB.start();

            MEM.run();            
            if (MEM.is_not_finished()) continue;
            else if (MEM.catch_hazard()) {
                MEM.solve_hazard(); 
                //MEM.restart();
                continue;
            } else MEM.start();

            EX.run();            
            if (EX.is_not_finished()) continue;
            else if (EX.catch_hazard()) {
                EX.solve_hazard(); 
                //EX.restart();
                pipline_flush();
                continue;
            } else EX.start();

            ID.run(); 
            if (id_ex.IR == 0x0ff00513) rst = true;
            if (rst) id_ex.IR = NOP;
            if (ID.is_not_finished()) continue;
            else if (ID.catch_hazard()) {
                ID.solve_hazard(); 
                ID.restart();
                continue;
            } else ID.start();

            IF.run();    
            if (IF.is_not_finished()) continue;
            else if (IF.catch_hazard()) {
                IF.solve_hazard(); 
                //IF.restart();
                continue;
            } else IF.start(clk);
        }
            //stage(IF, ID, EX, MEM, WB, rst);
        //print();
        printf("%d\n", int(RegisterFile.read(10) & 255u));
    }
};

}