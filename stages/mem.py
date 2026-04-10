from core.latches import MEM_WB_Latch

class MemStage:
    def __init__(self):
        self.store_buffer = [] # list of dicts
        self.MAX_SB_SIZE = 4
        self.sb_latency_remaining = 0

    def tick(self, cache_hierarchy):
        if self.sb_latency_remaining > 0:
            self.sb_latency_remaining -= 1
        elif len(self.store_buffer) > 0:
            st = self.store_buffer.pop(0)
            if st["size"] == 4:
                lat = cache_hierarchy.store_word(st["address"], st["value"])
            else:
                lat = cache_hierarchy.store_byte(st["address"], st["value"])
            self.sb_latency_remaining = lat
            if self.sb_latency_remaining > 0: 
                self.sb_latency_remaining -= 1 # 1 cycle overlaps with current tick

    def is_sb_full(self):
        return len(self.store_buffer) >= self.MAX_SB_SIZE

    def flush_all(self, cache_hierarchy):
        while self.store_buffer:
            st = self.store_buffer.pop(0)
            if st["size"] == 4:
                cache_hierarchy.store_word(st["address"], st["value"])
            else:
                cache_hierarchy.store_byte(st["address"], st["value"])

    def step(self, ex_mem_latch, stall, cache_hierarchy):
        if stall or ex_mem_latch.is_nop:
            return MEM_WB_Latch(is_nop=True), 0
            
        mem_data = 0
        latency = 0
        
        if ex_mem_latch.mem_read:
            # 1. Forwarding from Store Buffer
            forwarded = False
            for st in reversed(self.store_buffer):
                if st["address"] == ex_mem_latch.alu_result and st["size"] == ex_mem_latch.mem_size:
                    mem_data = st["value"]
                    latency = 1 # fast cache hit / store-to-load forwarding
                    forwarded = True
                    break
            if not forwarded:
                if ex_mem_latch.mem_size == 1:
                    mem_data, latency = cache_hierarchy.load_byte(ex_mem_latch.alu_result)
                elif ex_mem_latch.mem_size == 4:
                    mem_data, latency = cache_hierarchy.load_word(ex_mem_latch.alu_result)
        elif ex_mem_latch.mem_write:
            # Mask cache latency, pipeline only sees 1 cycle latency
            latency = 1
            self.store_buffer.append({
                "address": ex_mem_latch.alu_result,
                "value": ex_mem_latch.rs2_val,
                "size": ex_mem_latch.mem_size
            })
            
        return MEM_WB_Latch(
            is_nop=False,
            alu_result=ex_mem_latch.alu_result,
            mem_data=mem_data,
            rd_addr=ex_mem_latch.rd_addr,
            reg_write=ex_mem_latch.reg_write,
            mem_to_reg=ex_mem_latch.mem_read
        ), latency