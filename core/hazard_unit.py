class HazardUnit:
    def detect(self, if_id, id_ex, ex_mem, mem_wb):
        forwardA = "NONE"
        forwardB = "NONE"
        forwardC="NONE"
        forwardD="NONE"
        stall = False

        if not ex_mem.is_nop and not id_ex.is_nop and ex_mem.reg_write and not ex_mem.mem_read and ex_mem.rd_addr != 0:
            if ex_mem.rd_addr==id_ex.rs1_addr:
                forwardA="ex_mem"
            if ex_mem.rd_addr==id_ex.rs2_addr:
                forwardB="ex_mem"
 
        if not mem_wb.is_nop and not id_ex.is_nop and mem_wb.reg_write and mem_wb.rd_addr != 0:
            if mem_wb.rd_addr==id_ex.rs1_addr and forwardA=="NONE":
                forwardA="mem_wb"
            if mem_wb.rd_addr==id_ex.rs2_addr and forwardB=="NONE":
                forwardB="mem_wb"
 
        if not id_ex.is_nop and not if_id.is_nop and id_ex.alu_op=="lw" and id_ex.rd_addr!=0:
            if id_ex.rd_addr==if_id.instruction.rs1 or id_ex.rd_addr==if_id.instruction.rs2:
                stall="decode"

        if not if_id.is_nop and if_id.instruction.opcode in ["beq", "bne"]:
            branch_rs1 = if_id.instruction.rs1
            branch_rs2 = if_id.instruction.rs2

            if not id_ex.is_nop and id_ex.reg_write and id_ex.rd_addr != 0:
                if id_ex.rd_addr == branch_rs1 or id_ex.rd_addr == branch_rs2:
                    stall = "decode" 
            if not ex_mem.is_nop and not ex_mem.mem_read and ex_mem.reg_write:
                if ex_mem.rd_addr == branch_rs1:
                    forwardC = "ex_mem"
                if ex_mem.rd_addr == branch_rs2:
                    forwardD = "ex_mem"
            if not mem_wb.is_nop and  mem_wb.mem_to_reg :
                if mem_wb.rd_addr == branch_rs1:
                    forwardC = "mem_wb"
                if mem_wb.rd_addr == branch_rs2:
                    forwardD = "mem_wb"        
            if not ex_mem.is_nop and ex_mem.reg_write and ex_mem.rd_addr != 0 and  ex_mem.mem_read:
                if ex_mem.rd_addr == branch_rs1 or ex_mem.rd_addr == branch_rs2:
                    stall = "execute"

        return forwardA, forwardB,forwardC,forwardD, stall
