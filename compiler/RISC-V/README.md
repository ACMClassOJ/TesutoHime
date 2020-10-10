# RISC-V
2020 RISC-V 指令集模拟器

- lui
将符号位扩展的 20 位立即数 immediate 左移 12 位，并将低 12 位置零，写入 x[rd]中
x[rd] = sext(immediate[31:12] << 12) 

- auipc
把符号位扩展的 20 位（左移 12 位）立即数加到 pc 上，结果写入 x[rd]。 
x[rd] = pc + sext(immediate[31:12] << 12)

- jal
把下一条指令的地址(pc+4)，然后把pc设置为当前值加上符号位扩展的offset。 rd默认为x1
x[rd] = pc+4; pc += sext(offset) 

- jalr
把 pc 设置为 x[rs1] + sign-extend(offset)，把计算出的地址的最低有效位设为 0，并将原 pc+4 的值写入 f[rd]。rd 默认为 x1。 
t =pc+4; pc=(x[rs1]+sext(offset))&~1; x[rd]=t 

- beq
若寄存器 x[rs1]和寄存器 x[rs2]的值相等，把 pc的值设为当前值加上符号位扩展的偏移 offset。
if (rs1 == rs2) pc += sext(offset) 

- bne
blt
bge
bltu
bgeu