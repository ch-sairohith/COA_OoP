class DecodeStage:
    def __init__(self, register_file):
        self.register_file = register_file

    def step(self, if_id_latch, id_ex_latch, ex_mem_latch, mem_wb_latch, fwd_branch_rs1, fwd_branch_rs2, stall_signal: bool):
        if stall_signal or if_id_latch.is_nop:
            id_ex_latch.is_nop = True
            return None, False

        instr = if_id_latch.instruction
        pc = if_id_latch.pc

        if fwd_branch_rs1=="ex_mem": rs1_val=ex_mem_latch.alu_result
        elif fwd_branch_rs1=="mem_wb": rs1_val=mem_wb_latch.mem_data if mem_wb_latch.mem_to_reg else mem_wb_latch.alu_result
        else: rs1_val = self.register_file.read(instr.rs1) if instr.rs1 is not None else 0

        if fwd_branch_rs2=="ex_mem": rs2_val=ex_mem_latch.alu_result
        elif fwd_branch_rs2=="mem_wb": rs2_val=mem_wb_latch.mem_data if mem_wb_latch.mem_to_reg else mem_wb_latch.alu_result
        else: rs2_val = self.register_file.read(instr.rs2) if instr.rs2 is not None else 0

        reg_write, mem_read, mem_write, mem_to_reg, is_branch = False, False, False, False, False
        mem_size = 0  
        target_pc = None
        flush_if = False

        if instr.opcode in ["add", "sub", "addi", "la", "slt", "mul"]:
            reg_write = True
        elif instr.opcode == "lw":
            mem_read, reg_write, mem_to_reg, mem_size = True, True, True, 4
        elif instr.opcode == "sw":
            mem_write, mem_size = True, 4
        elif instr.opcode in ["beq", "bne"]:
            is_branch = True
            branch_taken = (instr.opcode == "beq" and rs1_val == rs2_val) or (instr.opcode == "bne" and rs1_val != rs2_val)
            if branch_taken:
                target_pc = pc + instr.imm 
                flush_if = True
                id_ex_latch.is_nop = True  
                return target_pc, flush_if
        elif instr.opcode == "jal":
            reg_write, is_branch, flush_if = True, True, True
            target_pc = pc + instr.imm

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
        id_ex_latch.mem_size = mem_size
        id_ex_latch.counter = 0  
        id_ex_latch.needs_translation = getattr(instr, 'needs_translation', False)
        
        return target_pc, flush_if