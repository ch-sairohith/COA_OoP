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
                    # Only upgrade stall to 'decode' if no stronger stall is already set
                    if stall is False:
                        stall = "decode"
            # Bug 4 fix: added rd_addr != 0 guard
            if not ex_mem.is_nop and not ex_mem.mem_read and ex_mem.reg_write and ex_mem.rd_addr != 0:
                if ex_mem.rd_addr == branch_rs1:
                    forwardC = "ex_mem"
                if ex_mem.rd_addr == branch_rs2:
                    forwardD = "ex_mem"
            if not mem_wb.is_nop and mem_wb.mem_to_reg and mem_wb.rd_addr != 0:
                if mem_wb.rd_addr == branch_rs1 and forwardC == "NONE":
                    forwardC = "mem_wb"
                if mem_wb.rd_addr == branch_rs2 and forwardD == "NONE":
                    forwardD = "mem_wb"
            if not ex_mem.is_nop and ex_mem.reg_write and ex_mem.rd_addr != 0 and ex_mem.mem_read:
                if ex_mem.rd_addr == branch_rs1 or ex_mem.rd_addr == branch_rs2:
                    stall = "execute"

        return forwardA, forwardB,forwardC,forwardD, stall

    def detect_nonforwarding(self, if_id, id_ex, ex_mem, mem_wb):
        """
        Non-forwarding hazard detection (parallel execution model).
        All stages read their latch snapshots simultaneously at the start
        of the cycle — WB has NOT written to the register file yet when
        Decode reads it. So ALL three downstream latches must be checked.
        """
        stall = False

        if if_id.is_nop:
            return stall

        rs1 = if_id.instruction.rs1
        rs2 = if_id.instruction.rs2

        # ID/EX: pending write, 2 cycles before WB → stall
        if not id_ex.is_nop and id_ex.reg_write and id_ex.rd_addr != 0:
            if (rs1 is not None and id_ex.rd_addr == rs1) or (rs2 is not None and id_ex.rd_addr == rs2):
                stall = True

        # EX/MEM: pending write, 1 cycle before WB → stall
        if not ex_mem.is_nop and ex_mem.reg_write and ex_mem.rd_addr != 0:
            if (rs1 is not None and ex_mem.rd_addr == rs1) or (rs2 is not None and ex_mem.rd_addr == rs2):
                stall = True

        # MEM/WB: WB hasn't written yet this cycle (parallel model) → stall
        if not mem_wb.is_nop and mem_wb.reg_write and mem_wb.rd_addr != 0:
            if (rs1 is not None and mem_wb.rd_addr == rs1) or (rs2 is not None and mem_wb.rd_addr == rs2):
                stall = True

        return stall
