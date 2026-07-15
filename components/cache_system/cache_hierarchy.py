from components.cache_system.cache import Cache
from components.cache_system.memory_controller import MemoryController

class CacheHierarchy:
    @staticmethod
    def _data_byte(block, offset):
        b = block[offset]
        if isinstance(b, int):
            return b & 0xFF
        return 0

    @staticmethod
    def _word_to_bytes(value):
        val = value & 0xFFFFFFFF
        return [
            val & 0xFF,
            (val >> 8) & 0xFF,
            (val >> 16) & 0xFF,
            (val >> 24) & 0xFF
        ]

    @staticmethod
    def _bytes_to_word(b0, b1, b2, b3):
        value = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
        if value >= 0x80000000:
            value -= 0x100000000
        return value

    def __init__(self, config, data_memory, inst_memory):
        self.L1I = Cache(**config["L1I"])
        self.L1D = Cache(**config["L1D"])
        self.L2 = Cache(**config["L2"])
        self.data_memory = data_memory
        self.inst_memory = inst_memory
        
        self.memory_latency = config["MEMORY_LATENCY"]
        self.mem_ctrl = MemoryController(data_memory, self.memory_latency)
        
    def tick(self):
        self.mem_ctrl.tick()

    def _get_data_block(self, address, block_size):
        base = address - (address % block_size)
        block = [0] * block_size
        for i in range(block_size):
            try:
                block[i] = self.data_memory.read_byte(base + i)
            except Exception:
                pass
        return block

    def _get_instruction_block(self, address, block_size):
        base = address - (address % block_size)
        block = [None] * block_size
        num_instructions = block_size // 4
        for i in range(num_instructions):
            inst_pc = base + (i * 4)
            block[i * 4] = self.inst_memory.read(inst_pc)
        return block

    def _insert_l2(self, address, block, dirty=False):
        penalty = 0
        evicted_info = self.L2.insert(address, block, dirty=dirty)
        if evicted_info:
            evicted_addr, evicted_data, evicted_dirty = evicted_info
            
            wb_l1d = self.L1D.invalidate(evicted_addr)
            if wb_l1d:
                evicted_data = wb_l1d[1]
                evicted_dirty = True
                
            self.L1I.invalidate(evicted_addr)
            
            if evicted_dirty:
                penalty += self.mem_ctrl.enqueue_write(evicted_addr, evicted_data)
        return penalty

    def fetch(self, address):
        latency = 0
        hit, value = self.L1I.read(address)
        latency += self.L1I.latency
        if hit:
            return value, latency
            
        latency += self.L2.latency
        block = self.L2.read_block(address, update_stats=True)
        if block is not None:
            offset = address % self.L1I.block_size
            value = block[offset]
            wb = self.L1I.insert(address, block)
            if wb: 
                evicted_addr, evicted_data, evicted_dirty = wb
                if evicted_dirty:
                    latency += self._insert_l2(evicted_addr, evicted_data, dirty=True)
            return value, latency
            
        latency += self.memory_latency
        block = self._get_instruction_block(address, self.L1I.block_size)
        latency += self._insert_l2(address, block)
        wb1 = self.L1I.insert(address, block)
        if wb1: 
            evicted_addr, evicted_data, evicted_dirty = wb1
            if evicted_dirty:
                latency += self._insert_l2(evicted_addr, evicted_data, dirty=True)
                
        offset = address % self.L1I.block_size
        return block[offset], latency

    def _ensure_data_block(self, address):
        latency = 0
        latency += self.L1D.latency
        block = self.L1D.read_block(address, update_stats=True)
        if block is not None:
            return block, latency
            
        latency += self.L2.latency
        block = self.L2.read_block(address, update_stats=True)
        if block is not None:
            wb = self.L1D.insert(address, block)
            if wb: 
                evicted_addr, evicted_data, evicted_dirty = wb
                if evicted_dirty:
                    latency += self._insert_l2(evicted_addr, evicted_data, dirty=True)
            return block, latency
            
        latency += self.memory_latency
        block = self._get_data_block(address, self.L1D.block_size)
        latency += self._insert_l2(address, block)
        wb1 = self.L1D.insert(address, block)
        if wb1: 
            evicted_addr, evicted_data, evicted_dirty = wb1
            if evicted_dirty:
                latency += self._insert_l2(evicted_addr, evicted_data, dirty=True)
        return block, latency

    def _handle_unaligned_access(self, address, is_store, bytes_list=None):
        latency = 0
        visited_blocks = set()
        block_size = self.L1D.block_size
        read_bytes = []
        
        for i in range(4):
            addr = address + i
            block_addr = addr - (addr % block_size)
            if block_addr not in visited_blocks:
                byte_block, lat = self._ensure_data_block(addr)
                latency += lat
                visited_blocks.add(block_addr)
            else:
                byte_block = self.L1D.read_block(addr, update_stats=False)
                
            inner_offset = addr % block_size
            if is_store:
                self.L1D.write(addr, bytes_list[i])
            else:
                read_bytes.append(self._data_byte(byte_block, inner_offset))
                
        if not is_store:
            return self._bytes_to_word(*read_bytes), latency
        return latency

    def load_word(self, address):
        if address % 4 != 0:
            raise Exception("Address must be 4-byte aligned")
            
        block_size = self.L1D.block_size
        offset = address % block_size
        
        if offset + 3 >= block_size:
            return self._handle_unaligned_access(address, is_store=False)
            
        block, latency = self._ensure_data_block(address)
        return self._bytes_to_word(
            self._data_byte(block, offset),
            self._data_byte(block, offset + 1),
            self._data_byte(block, offset + 2),
            self._data_byte(block, offset + 3)
        ), latency

    def store_word(self, address, value):
        if address % 4 != 0:
            raise Exception("Address must be 4-byte aligned")
            
        block_size = self.L1D.block_size
        offset = address % block_size
        bytes_list = self._word_to_bytes(value)
        
        if offset + 3 >= block_size:
            return self._handle_unaligned_access(address, is_store=True, bytes_list=bytes_list)
            
        _, latency = self._ensure_data_block(address)
        for i in range(4):
            self.L1D.write(address + i, bytes_list[i])
        return latency

    def load_byte(self, address):
        block, latency = self._ensure_data_block(address)
        offset = address % self.L1D.block_size
        return self._data_byte(block, offset), latency

    def store_byte(self, address, value):
        _, latency = self._ensure_data_block(address)
        self.L1D.write(address, value)
        return latency

    def get_stats(self):
        return {
            "L1I Miss Rate": self.L1I.misses / max(1, (self.L1I.hits + self.L1I.misses)),
            "L1D Miss Rate": self.L1D.misses / max(1, (self.L1D.hits + self.L1D.misses)),
            "L2 Miss Rate": self.L2.misses / max(1, (self.L2.hits + self.L2.misses)),
        }

    def flush_all(self):
        for s in self.L1D.sets:
            for l in s.lines:
                if l.valid and l.dirty:
                    base_addr = self.L1D._reconstruct_address(l.tag, self.L1D.sets.index(s))
                    self.mem_ctrl.enqueue_write(base_addr, l.data)
                    self.L2.invalidate(base_addr)
                    l.dirty = False
                    
        for s in self.L2.sets:
            for l in s.lines:
                if l.valid and l.dirty:
                    base_addr = self.L2._reconstruct_address(l.tag, self.L2.sets.index(s))
                    self.mem_ctrl.enqueue_write(base_addr, l.data)
                    l.dirty = False
                    
        self.mem_ctrl.flush()
