
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

    def step(self, ex_mem_latch, stall, cache_hierarchy, translator=None):
        if stall or ex_mem_latch.is_nop:
            return MEM_WB_Latch(is_nop=True), 0
            
        paddr, vm_latency = self._translate_address(ex_mem_latch, translator)
        
        mem_data, latency = 0, 0
        if ex_mem_latch.mem_read:
            mem_data, latency = self._handle_load(paddr, ex_mem_latch.mem_size, cache_hierarchy)
        elif ex_mem_latch.mem_write:
            latency = self._handle_store(paddr, ex_mem_latch.rs2_val, ex_mem_latch.mem_size)
            
        return self._create_output_latch(ex_mem_latch, mem_data), latency + vm_latency

    def _translate_address(self, latch, translator):
        if getattr(latch, 'needs_translation', False) and translator is not None:
            return translator.translate(latch.alu_result, is_write=latch.mem_write)
        return latch.alu_result, 0

    def _handle_load(self, paddr, size, cache_hierarchy):
        # 1. Check for Store-to-Load Forwarding (Cache bypass)
        for st in reversed(self.store_buffer):
            if st["address"] == paddr and st["size"] == size:
                return st["value"], 1 # Fast 1-cycle hit

        # 2. Fetch from Cache Hierarchy
        if size == 1:
            return cache_hierarchy.load_byte(paddr)
        return cache_hierarchy.load_word(paddr)

    def _handle_store(self, paddr, value, size):
        # Mask cache latency, pipeline only sees 1-cycle latency
        self.store_buffer.append({"address": paddr, "value": value, "size": size})
        return 1

    def _create_output_latch(self, in_latch, mem_data):
        return MEM_WB_Latch(
            is_nop=False,
            alu_result=in_latch.alu_result,
            mem_data=mem_data,
            rd_addr=in_latch.rd_addr,
            reg_write=in_latch.reg_write,
            mem_to_reg=in_latch.mem_read
        )
