class ExecuteStage:
  def step(self, id_ex_latch, ex_mem_latch, mem_wb_latch, forwardA, forwardB, stall):
        """
        Executes one clock cycle of the Execute stage.
        """
        if stall or id_ex_latch.is_nop:
            ex_mem_latch.is_nop = True
            return

        if forwardA == "ex_mem":
            rs1_val=ex_mem_latch.alu_result
        elif forwardA=="mem_wb":
            if mem_wb_latch.mem_to_reg:
                rs1_val=mem_wb_latch.mem_data
            else:
                rs1_val=mem_wb_latch.alu_result
        else:
            rs1_val = id_ex_latch.rs1_val

        if forwardB == "ex_mem":
            rs2_val=ex_mem_latch.alu_result
        elif forwardB=="mem_wb":
            if mem_wb_latch.mem_to_reg:
                rs2_val=mem_wb_latch.mem_data
            else:
                rs2_val=mem_wb_latch.alu_result
        else:
            rs2_val = id_ex_latch.rs2_val

        instr = id_ex_latch.instruction
        imm = id_ex_latch.imm

        alu_result = 0
        
        if instr.opcode == "add":
            alu_result = rs1_val + rs2_val
        elif instr.opcode in ["addi", "la"]:
            alu_result = rs1_val + imm
        elif instr.opcode == "sub":
            alu_result = rs1_val - rs2_val
        elif instr.opcode == "slt":
            if rs1_val < rs2_val:
                alu_result=1
            else:
                alu_result=0
        elif instr.opcode in ["lw", "sw"]:
            alu_result = rs1_val + imm 
        elif instr.opcode in ["beq", "bne"]:
            alu_result = rs1_val - rs2_val 
        elif instr.opcode == "jal":
            alu_result = id_ex_latch.pc + 4  

        ex_mem_latch.is_nop = False
        ex_mem_latch.alu_result = alu_result
        ex_mem_latch.rd_addr = id_ex_latch.rd_addr
        ex_mem_latch.rs2_val = rs2_val
        ex_mem_latch.mem_size = 4 if instr.opcode in ["lw", "sw"] else 0
        ex_mem_latch.mem_read = id_ex_latch.mem_read
        ex_mem_latch.mem_write = id_ex_latch.mem_write
        ex_mem_latch.reg_write = id_ex_latch.reg_write
    
