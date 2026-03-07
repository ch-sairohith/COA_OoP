class ExecuteStage:
  def step(self,ID_EX_Latch, EX_MEM_Latch,MEM_WB_Latch,forwardA,forwardB,stall):
        """
        Executes one clock cycle of the Execute stage.
        """
        if stall or ID_EX_Latch.is_nop:
            EX_MEM_Latch.is_nop = True
            return

        if forwardA == "ex_mem":
            rs1_val=EX_MEM_Latch.alu_result
        elif forwardA=="mem_wb":
            if MEM_WB_Latch.mem_to_reg:
                rs1_val=MEM_WB_Latch.mem_data
            else:
                rs1_val=MEM_WB_Latch.alu_result
        else:
            rs1_val = ID_EX_Latch.rs1_val

        if forwardB == "ex_mem":
            rs2_val=EX_MEM_Latch.alu_result
        elif forwardB=="mem_wb":
            if MEM_WB_Latch.mem_to_reg:
                rs2_val=MEM_WB_Latch.mem_data
            else:
                rs2_val=MEM_WB_Latch.alu_result
        else:
            rs2_val = ID_EX_Latch.rs2_val

        instr = ID_EX_Latch.instruction
        imm = ID_EX_Latch.imm

        alu_result = 0
        
        if instr.opcode == "add":
            alu_result = rs1_val + rs2_val
        elif instr.opcode in ["addi", "la"]:
            alu_result = rs1_val + imm
        elif instr.opcode == "sub":
            alu_result = rs1_val - rs2_val
        elif instr.opcode in ["lw", "sw"]:
            alu_result = rs1_val + imm 
        elif instr.opcode in ["beq", "bne"]:
            alu_result = rs1_val - rs2_val 
        elif instr.opcode == "jal":
            alu_result = ID_EX_Latch.pc + 4  

        EX_MEM_Latch.is_nop = False
        EX_MEM_Latch.alu_result = alu_result
        EX_MEM_Latch.rd_addr = ID_EX_Latch.rd_addr
        EX_MEM_Latch.rs2_val = rs2_val
        EX_MEM_Latch.mem_size = 4 if instr.opcode in ["lw", "sw"] else 0
        EX_MEM_Latch.mem_read = ID_EX_Latch.mem_read
        EX_MEM_Latch.mem_write = ID_EX_Latch.mem_write
        EX_MEM_Latch.reg_write = ID_EX_Latch.reg_write
    
