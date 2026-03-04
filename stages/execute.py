class ExecuteStage:
  def step(ID_EX_Latch, EX_MEM_Latch, stall):
        """
        Executes one clock cycle of the Execute stage.
        """
        if stall or ID_EX_Latch.is_nop:
            EX_MEM_Latch.is_nop = True
            return

        instr = ID_EX_Latch.instruction
        rs1_val = ID_EX_Latch.rs1_val
        rs2_val = ID_EX_Latch.rs2_val
        imm = ID_EX_Latch.imm

        alu_result = 0
        
        if instr.opcode in ["add", "addi", "la"]:
            alu_result = rs1_val + (imm if instr.opcode == "addi" else 0)
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
        
        EX_MEM_Latch.mem_read = ID_EX_Latch.mem_read
        EX_MEM_Latch.mem_write = ID_EX_Latch.mem_write
    