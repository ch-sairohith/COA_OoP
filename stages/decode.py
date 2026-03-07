class DecodeStage:
    def __init__(self, register_file):
        """
        Initializes Decode with access to the hardware Register File.
        """
        self.register_file = register_file

    def step(self, if_id_latch, id_ex_latch,ex_mem_latch,mem_wb_latch,forwardA,forwardB, stall: bool):
        """
        Executes one clock cycle of the Decode stage.
        Returns a tuple: (target_pc, flush_if) for early branch resolution.
        """
        if stall or if_id_latch.is_nop:
            id_ex_latch.is_nop = True
            return None, False

        instr = if_id_latch.instruction
        pc = if_id_latch.pc

        if forwardA=="ex_mem":
            rs1_val=ex_mem_latch.alu_result
        elif forwardA=="mem_wb":
            if mem_wb_latch.mem_to_reg:
                rs1_val=mem_wb_latch.mem_data
            else:
                rs1_val=mem_wb_latch.alu_result
        else:
            rs1_val = self.register_file.read(instr.rs1) if instr.rs1 is not None else 0

        if forwardB=="ex_mem":
            rs2_val=ex_mem_latch.alu_result
        elif forwardB=="mem_wb":
            if mem_wb_latch.mem_to_reg:
                rs2_val=mem_wb_latch.mem_data
            else:
                rs2_val=mem_wb_latch.alu_result
        else:
            rs2_val = self.register_file.read(instr.rs2) if instr.rs2 is not None else 0

        reg_write = False
        mem_read = False
        mem_write = False
        mem_to_reg = False
        is_branch = False
        
        target_pc = None
        flush_if = False

        if instr.opcode in ["add", "sub", "addi", "la", "slt"]:
            reg_write = True
            
        elif instr.opcode == "lw":
            mem_read = True
            reg_write = True
            mem_to_reg = True 
            
        elif instr.opcode == "sw":
            mem_write = True
            
        elif instr.opcode in ["beq", "bne"]:
            is_branch = True
            
            branch_taken = (instr.opcode == "beq" and rs1_val == rs2_val) or (instr.opcode == "bne" and rs1_val != rs2_val)
                           
            if branch_taken:
                target_pc = pc + instr.imm 
                flush_if = True
                
                # Turn the branch itself into a NOP for the EX stage, 
                # because its work is already completely done!
                id_ex_latch.is_nop = True  
                return target_pc, flush_if
            
        elif instr.opcode == "jal":
            reg_write = True
            is_branch = True 
            
            # JAL is an unconditional jump, so it always resolves early
            target_pc = pc + instr.imm
            flush_if = True
            
            # Note: We do NOT make JAL a NOP for EX! It still needs to travel 
            # down the pipeline to write the return address (PC+4) to the rd register.

        id_ex_latch.is_nop = False
        id_ex_latch.pc = pc
        id_ex_latch.instruction = instr
        
        id_ex_latch.rs1_val = rs1_val
        id_ex_latch.rs2_val = rs2_val
        id_ex_latch.rs1_addr = instr.rs1
        id_ex_latch.rs2_addr = instr.rs2
        id_ex_latch.rd_addr = instr.rd
        
        id_ex_latch.imm = instr.imm if instr.imm is not None else 0
        
        id_ex_latch.alu_op = instr.opcode
        id_ex_latch.reg_write = reg_write
        id_ex_latch.mem_read = mem_read
        id_ex_latch.mem_write = mem_write
        id_ex_latch.mem_to_reg = mem_to_reg
        id_ex_latch.is_branch = is_branch
        
        return target_pc, flush_if
