import json

class HazardUnit:
    def __init__(self):
        with open("config.json", "r") as file:
            config = json.load(file)
        self.latency_lw = config["latencies"].get("lw", 1)
        self.latency_sw = config["latencies"].get("sw", 1)
        self.latency_add = config["latencies"].get("add", 1)
        self.latency_mul = config["latencies"].get("mul", 3)

    def detect(self, if_id, id_ex, ex_mem, mem_wb, isforward: bool = True):
        """
        Orchestrates hazard detection, execution timers, and pipeline forwarding.
        """
        # 1. Execution Delays (Always checked, regardless of forwarding mode)
        stall_signal = self._check_execution_delays(id_ex)
        
        # 2. Data Hazards & Forwarding
        if isforward:
            fwd_alu_rs1, fwd_alu_rs2, fwd_branch_rs1, fwd_branch_rs2 = self._get_forwarding(if_id, id_ex, ex_mem, mem_wb)
            if not stall_signal:
                stall_signal = self._get_stalls(if_id, id_ex, ex_mem)
        else:
            # Forwarding is disabled: cut the wires and check for RAW dependencies
            fwd_alu_rs1, fwd_alu_rs2, fwd_branch_rs1, fwd_branch_rs2 = "NONE", "NONE", "NONE", "NONE"
            if not stall_signal:
                if self._check_nonforwarding_hazards(if_id, id_ex, ex_mem, mem_wb):
                    stall_signal = True
                    
        return fwd_alu_rs1, fwd_alu_rs2, fwd_branch_rs1, fwd_branch_rs2, stall_signal

    def _get_forwarding(self, if_id, id_ex, ex_mem, mem_wb):
        """Bundles all forwarding logic together."""
        fwd_alu_rs1, fwd_alu_rs2 = self._get_alu_forwarding(id_ex, ex_mem, mem_wb)
        fwd_branch_rs1, fwd_branch_rs2 = self._get_branch_forwarding(if_id, ex_mem, mem_wb)
        return fwd_alu_rs1, fwd_alu_rs2, fwd_branch_rs1, fwd_branch_rs2

    def _get_stalls(self, if_id, id_ex, ex_mem):
        """Bundles all data stall logic together (when forwarding is enabled)."""
        stall_signal = self._check_load_use_hazards(if_id, id_ex)
        if not stall_signal:
            stall_signal = self._check_branch_hazards(if_id, id_ex, ex_mem)
        return stall_signal

    def _get_alu_forwarding(self, id_ex, ex_mem, mem_wb):
        """Calculates forwarding paths for ALU operations in Execute Stage."""
        fwd_alu_rs1, fwd_alu_rs2 = "NONE", "NONE"
        
        # 1. EX Hazard (Highest Priority)
        if not ex_mem.is_nop and not id_ex.is_nop and ex_mem.reg_write and not ex_mem.mem_read and ex_mem.rd_addr != 0:
            if ex_mem.rd_addr == id_ex.rs1_addr: fwd_alu_rs1 = "ex_mem"
            if ex_mem.rd_addr == id_ex.rs2_addr: fwd_alu_rs2 = "ex_mem"
            
        # 2. MEM Hazard (Lower Priority)
        if not mem_wb.is_nop and not id_ex.is_nop and mem_wb.reg_write and mem_wb.rd_addr != 0:
            if mem_wb.rd_addr == id_ex.rs1_addr and fwd_alu_rs1 == "NONE": fwd_alu_rs1 = "mem_wb"
            if mem_wb.rd_addr == id_ex.rs2_addr and fwd_alu_rs2 == "NONE": fwd_alu_rs2 = "mem_wb"
            
        return fwd_alu_rs1, fwd_alu_rs2

    def _get_branch_forwarding(self, if_id, ex_mem, mem_wb):
        """Calculates forwarding paths for Early Branch Resolution in Decode Stage."""
        fwd_branch_rs1, fwd_branch_rs2 = "NONE", "NONE"
        if not if_id.is_nop:
            if isinstance(if_id.instruction, int):
                pass
            elif if_id.instruction.opcode in ["beq", "bne"]:
                branch_rs1 = if_id.instruction.rs1
                branch_rs2 = if_id.instruction.rs2
                
                if not ex_mem.is_nop and not ex_mem.mem_read and ex_mem.reg_write and ex_mem.rd_addr != 0:
                    if ex_mem.rd_addr == branch_rs1: fwd_branch_rs1 = "ex_mem"
                    if ex_mem.rd_addr == branch_rs2: fwd_branch_rs2 = "ex_mem"
                    
                if not mem_wb.is_nop and mem_wb.mem_to_reg and mem_wb.rd_addr != 0:
                    if mem_wb.rd_addr == branch_rs1 and fwd_branch_rs1 == "NONE": fwd_branch_rs1 = "mem_wb"
                    if mem_wb.rd_addr == branch_rs2 and fwd_branch_rs2 == "NONE": fwd_branch_rs2 = "mem_wb"
                
        return fwd_branch_rs1, fwd_branch_rs2

    def _check_execution_delays(self, id_ex):
        """Handles structural stall counters for multi-cycle arithmetic (add, mul)."""
        stall_signal = False
        if not id_ex.is_nop:
            if id_ex.alu_op == "add":
                if self.latency_add > 1 and id_ex.counter < self.latency_add - 1:
                    stall_signal = "execute"
                    id_ex.counter += 1
                    
            elif id_ex.alu_op == "mul":
                if self.latency_mul > 1 and id_ex.counter < self.latency_mul - 1:
                    stall_signal = "execute"
                    id_ex.counter += 1
        return stall_signal

    def _check_load_use_hazards(self, if_id, id_ex):
        """Handles 1-cycle Decode stall for Load-Use data hazard."""
        if not id_ex.is_nop and not if_id.is_nop and id_ex.alu_op == "lw" and id_ex.rd_addr != 0:
            if id_ex.rd_addr == if_id.instruction.rs1 or id_ex.rd_addr == if_id.instruction.rs2:
                return "decode"
        return False

    def _check_branch_hazards(self, if_id, id_ex, ex_mem):
        """Handles Decode stalls when a branch depends on EX or MEM."""
        if not if_id.is_nop and if_id.instruction.opcode in ["beq", "bne"]:
            branch_rs1 = if_id.instruction.rs1
            branch_rs2 = if_id.instruction.rs2
            
            if not id_ex.is_nop and id_ex.reg_write and id_ex.rd_addr != 0:
                if id_ex.rd_addr == branch_rs1 or id_ex.rd_addr == branch_rs2: 
                    return "decode"
                    
            if not ex_mem.is_nop and ex_mem.mem_read and ex_mem.reg_write and ex_mem.rd_addr != 0:
                if ex_mem.rd_addr == branch_rs1 or ex_mem.rd_addr == branch_rs2: 
                    return "decode"
                    
        return False

    def _check_nonforwarding_hazards(self, if_id, id_ex, ex_mem, mem_wb):
        """Baseline stall detection when data forwarding is disabled."""
        if if_id.is_nop: 
            return False

        rs1 = if_id.instruction.rs1
        rs2 = if_id.instruction.rs2

        if not id_ex.is_nop and id_ex.reg_write and id_ex.rd_addr != 0:
            if (rs1 is not None and id_ex.rd_addr == rs1) or (rs2 is not None and id_ex.rd_addr == rs2): 
                return True
                
        if not ex_mem.is_nop and ex_mem.reg_write and ex_mem.rd_addr != 0:
            if (rs1 is not None and ex_mem.rd_addr == rs1) or (rs2 is not None and ex_mem.rd_addr == rs2): 
                return True
                
        if not mem_wb.is_nop and mem_wb.reg_write and mem_wb.rd_addr != 0:
            if (rs1 is not None and mem_wb.rd_addr == rs1) or (rs2 is not None and mem_wb.rd_addr == rs2): 
                return True
                
        return False