from core.latches import EX_MEM_Latch

class ExecuteStage:
    def step(self, id_ex_latch, old_ex_mem_latch, mem_wb_latch, forwardA, forwardB, stall):
        if stall or id_ex_latch.is_nop:
            return EX_MEM_Latch(is_nop=True)

        if forwardA == "ex_mem": rs1_val = old_ex_mem_latch.alu_result
        elif forwardA == "mem_wb": rs1_val = mem_wb_latch.mem_data if mem_wb_latch.mem_to_reg else mem_wb_latch.alu_result
        else: rs1_val = id_ex_latch.rs1_val

        if forwardB == "ex_mem": rs2_val = old_ex_mem_latch.alu_result
        elif forwardB == "mem_wb": rs2_val = mem_wb_latch.mem_data if mem_wb_latch.mem_to_reg else mem_wb_latch.alu_result
        else: rs2_val = id_ex_latch.rs2_val

        instr = id_ex_latch.instruction
        imm = id_ex_latch.imm
        alu_result = 0
        
        if instr.opcode == "add": alu_result = rs1_val + rs2_val
        elif instr.opcode in ["addi", "la"]: alu_result = rs1_val + imm
        elif instr.opcode == "sub": alu_result = rs1_val - rs2_val
        elif instr.opcode == "slt": alu_result = 1 if rs1_val < rs2_val else 0
        elif instr.opcode in ["lw", "sw"]: alu_result = rs1_val + imm 
        elif instr.opcode in ["beq", "bne"]: alu_result = rs1_val - rs2_val 
        elif instr.opcode == "jal": alu_result = id_ex_latch.pc + 4  

        return EX_MEM_Latch(
            is_nop=False,
            alu_result=alu_result,
            rd_addr=id_ex_latch.rd_addr,
            rs2_val=rs2_val,
            mem_size=id_ex_latch.mem_size,
            mem_read=id_ex_latch.mem_read,
            mem_write=id_ex_latch.mem_write,
            reg_write=id_ex_latch.reg_write,
            counter=0  
        )