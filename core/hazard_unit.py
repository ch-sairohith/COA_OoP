import json

class HazardUnit:
    def __init__(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        self.latency_lw = config["latencies"].get("lw", 1)
        self.latency_sw = config["latencies"].get("sw", 1)
        self.latency_add = config["latencies"].get("add", 1)

    def detect(self, if_id, id_ex, ex_mem, mem_wb):
        forwardA, forwardB, forwardC, forwardD = "NONE", "NONE", "NONE", "NONE"
        stall = False

        # Multi-cycle D-cache / memory latency is handled in Simulator using
        # cache-reported latency (merged with config); not driven by ex_mem.counter here.

        if  not id_ex.is_nop and id_ex.alu_op == "add":
            if self.latency_add > 1 and id_ex.counter < self.latency_add - 1:
                if not stall:
                    stall="execute"
                id_ex.counter += 1

        if not ex_mem.is_nop and not id_ex.is_nop and ex_mem.reg_write and not ex_mem.mem_read and ex_mem.rd_addr != 0:
            if ex_mem.rd_addr == id_ex.rs1_addr: forwardA = "ex_mem"
            if ex_mem.rd_addr == id_ex.rs2_addr: forwardB = "ex_mem"
 
        if not mem_wb.is_nop and not id_ex.is_nop and mem_wb.reg_write and mem_wb.rd_addr != 0:
            if mem_wb.rd_addr == id_ex.rs1_addr and forwardA == "NONE": forwardA = "mem_wb"
            if mem_wb.rd_addr == id_ex.rs2_addr and forwardB == "NONE": forwardB = "mem_wb"
 
        if not stall:
            if not id_ex.is_nop and not if_id.is_nop and id_ex.alu_op == "lw" and id_ex.rd_addr != 0:
                if id_ex.rd_addr == if_id.instruction.rs1 or id_ex.rd_addr == if_id.instruction.rs2:
                    stall = "decode"

            if not if_id.is_nop and if_id.instruction.opcode in ["beq", "bne"]:
                branch_rs1 = if_id.instruction.rs1
                branch_rs2 = if_id.instruction.rs2
                if not id_ex.is_nop and id_ex.reg_write and id_ex.rd_addr != 0:
                    if id_ex.rd_addr == branch_rs1 or id_ex.rd_addr == branch_rs2: stall = "decode"
                if not ex_mem.is_nop and ex_mem.mem_read and ex_mem.reg_write and ex_mem.rd_addr != 0:
                    if ex_mem.rd_addr == branch_rs1 or ex_mem.rd_addr == branch_rs2: stall = "decode"

        if not if_id.is_nop and if_id.instruction.opcode in ["beq", "bne"]:
            branch_rs1 = if_id.instruction.rs1
            branch_rs2 = if_id.instruction.rs2
            if not ex_mem.is_nop and not ex_mem.mem_read and ex_mem.reg_write and ex_mem.rd_addr != 0:
                if ex_mem.rd_addr == branch_rs1: forwardC = "ex_mem"
                if ex_mem.rd_addr == branch_rs2: forwardD = "ex_mem"
            if not mem_wb.is_nop and mem_wb.mem_to_reg and mem_wb.rd_addr != 0:
                if mem_wb.rd_addr == branch_rs1 and forwardC == "NONE": forwardC = "mem_wb"
                if mem_wb.rd_addr == branch_rs2 and forwardD == "NONE": forwardD = "mem_wb"

        return forwardA, forwardB, forwardC, forwardD, stall

    def detect_nonforwarding(self, if_id, id_ex, ex_mem, mem_wb):
        stall = False
        if if_id.is_nop: return stall

        rs1 = if_id.instruction.rs1
        rs2 = if_id.instruction.rs2

        if not id_ex.is_nop and id_ex.reg_write and id_ex.rd_addr != 0:
            if (rs1 is not None and id_ex.rd_addr == rs1) or (rs2 is not None and id_ex.rd_addr == rs2): stall = True
        if not ex_mem.is_nop and ex_mem.reg_write and ex_mem.rd_addr != 0:
            if (rs1 is not None and ex_mem.rd_addr == rs1) or (rs2 is not None and ex_mem.rd_addr == rs2): stall = True
        if not mem_wb.is_nop and mem_wb.reg_write and mem_wb.rd_addr != 0:
            if (rs1 is not None and mem_wb.rd_addr == rs1) or (rs2 is not None and mem_wb.rd_addr == rs2): stall = True
        return stall