class HazardUnit:

    def detect(self, if_id, id_ex, ex_mem, mem_wb):

        forwardA = "NONE"
        forwardB = "NONE"
        stall = False

        #  EX → EX forwarding 
        if not ex_mem.is_nop and not id_ex.is_nop and ex_mem.reg_write and not ex_mem.mem_read and ex_mem.rd_addr != 0:
            if ex_mem.rd_addr==id_ex.rs1_addr:
                forwardA="ex_mem"
            if ex_mem.rd_addr==id_ex.rs2_addr:
                forwardB="ex_mem"

        #  MEM → EX forwarding 
        if not mem_wb.is_nop and not id_ex.is_nop and mem_wb.reg_write and mem_wb.rd_addr != 0:
            if mem_wb.rd_addr==id_ex.rs1_addr and forwardA=="NONE":
                forwardA="mem_wb"
            if mem_wb.rd_addr==id_ex.rs2_addr and forwardB=="NONE":
                forwardB="mem_wb"

        # Load-Use Hazard 
        if not id_ex.is_nop and not if_id.is_nop and id_ex.alu_op=="lw" and id_ex.rd_addr!=0:
            if id_ex.rd_addr==if_id.instruction.rs1 or id_ex.rd_addr==if_id.instruction.rs2:
                stall=True

        return forwardA, forwardB, stall


