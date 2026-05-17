from components.cache import Cache

class CacheHierarchy:
    @staticmethod
    def _data_byte(block, offset):
        """Unified L2 may hold sparse instruction blocks; treat non-byte slots as 0 for data reads."""
        b = block[offset]
        if isinstance(b, int):
            return b & 0xFF
        return 0

    def __init__(self,config,data_memory,inst_memory):
        self.L1I = Cache(**config["L1I"])
        self.L1D = Cache(**config["L1D"])
        self.L2 = Cache(**config["L2"])
        self.data_memory = data_memory
        self.inst_memory = inst_memory
        self.memory_latency = config["MEMORY_LATENCY"]
        self.wb_buffer = []               
        self.MAX_WB_SIZE = 4
        self.memory_busy_cycles = 0  
        self.active_write = None
        
    def tick(self):
        if self.memory_busy_cycles > 0:
            self.memory_busy_cycles -= 1
            if self.memory_busy_cycles == 0 and self.active_write:
                self._actual_write_back(self.active_write[0], self.active_write[1])
                self.active_write = None
                
        if self.memory_busy_cycles == 0 and self.wb_buffer:
            self.active_write = self.wb_buffer.pop(0)
            self.memory_busy_cycles = self.memory_latency

    def _read_block_from_cache(self,cache,address):
        #Helper to safely extract the entire data block from a cache on hit
        index, tag, offset = cache._get_index_tag_offset(address)
        cache_set = cache.sets[index]
        for line in cache_set.lines:
            if line.valid and line.tag == tag:
                return line.data
        return None

    def _get_data_block(self,address,block_size):
        base = address - (address % block_size)
        block = [0] * block_size
        for i in range(block_size):
            try:
                block[i] = self.data_memory.read_byte(base + i)
            except Exception:
                block[i] = 0
        return block

    def _get_instruction_block(self,address,block_size):
        base = address - (address % block_size)
        block = [None] * block_size
        num_instructions = block_size // 4
        for i in range(num_instructions):
            inst_pc = base + (i * 4)
            inst = self.inst_memory.read(inst_pc)
            block[i * 4] = inst
        return block

    def _actual_write_back(self,base_address,data):
        for i in range(len(data)):
            val = data[i]
            if isinstance(val, int): 
                try:
                    self.data_memory.store_byte(base_address + i, val)
                except Exception:
                    pass

    def _write_back(self, base_address, data):
        if len(self.wb_buffer) >= self.MAX_WB_SIZE:
             addr, old_data = self.wb_buffer.pop(0)
             self._actual_write_back(addr, old_data)
        self.wb_buffer.append((base_address, data))

    def _insert_l2(self, address, block, dirty=False):
        evicted_info = self.L2.insert(address, block, dirty=dirty)
        if evicted_info:
            evicted_addr, evicted_data, evicted_dirty = evicted_info
            
            # Enforce Inclusion
            wb_l1d = self.L1D.invalidate(evicted_addr)
            if wb_l1d:
                evicted_data = wb_l1d[1]
                evicted_dirty = True
                
            self.L1I.invalidate(evicted_addr)
            
            if evicted_dirty:
                self._write_back(evicted_addr, evicted_data)

    def fetch(self,address):
        latency = 0
        hit,value = self.L1I.read(address)
        latency += self.L1I.latency
        if hit:
            return value, latency
        hit2, value = self.L2.read(address)
        latency += self.L2.latency
        if hit2:
            block = self._read_block_from_cache(self.L2, address)
            wb = self.L1I.insert(address, block)
            if wb: 
                evicted_addr, evicted_data, evicted_dirty = wb
                if evicted_dirty:
                    self._insert_l2(evicted_addr, evicted_data, dirty=True)
            return value,latency
        latency += self.memory_latency
        block = self._get_instruction_block(address, self.L1I.block_size)
        self._insert_l2(address, block)
        wb1 = self.L1I.insert(address, block)
        if wb1: 
            evicted_addr, evicted_data, evicted_dirty = wb1
            if evicted_dirty:
                self._insert_l2(evicted_addr, evicted_data, dirty=True)
        offset = address % self.L1I.block_size
        return block[offset], latency

    def _ensure_data_block(self, address):
        #Guarantees the block exists in L1D, handling misses to Memory
        latency = 0
        # 1. Check L1D
        hit, _ = self.L1D.read(address)
        latency += self.L1D.latency
        if hit:
            return self._read_block_from_cache(self.L1D, address), latency
        # 2. Check L2
        hit2, _ = self.L2.read(address)
        latency += self.L2.latency
        if hit2:
            block = self._read_block_from_cache(self.L2, address)
            wb = self.L1D.insert(address, block)
            if wb: 
                evicted_addr, evicted_data, evicted_dirty = wb
                if evicted_dirty:
                    self._insert_l2(evicted_addr, evicted_data, dirty=True)
            return block, latency
        # 3. Main Memory
        latency += self.memory_latency
        block = self._get_data_block(address, self.L1D.block_size)
        self._insert_l2(address, block)
        wb1 = self.L1D.insert(address, block)
        if wb1: 
            evicted_addr, evicted_data, evicted_dirty = wb1
            if evicted_dirty:
                self._insert_l2(evicted_addr, evicted_data, dirty=True)
        return block, latency

    def load_word(self, address):
        if address % 4 != 0:
            raise Exception("Address must be 4-byte aligned")
        block_size = self.L1D.block_size
        offset = address % block_size
        if offset + 3 >= block_size:
            value = 0
            latency = 0
            visited_blocks = set()
            for i in range(4):
                addr = address + i
                block_addr = addr - (addr % block_size)
                if block_addr not in visited_blocks:
                    byte_block,lat = self._ensure_data_block(addr)
                    latency += lat
                    visited_blocks.add(block_addr) 
                inner_offset = (addr) % block_size
                value |= (self._data_byte(byte_block, inner_offset) << (8 * i))
            # Sign handling
            if value >= 0x80000000:
                value -= 0x100000000
            return value, latency
        block, latency = self._ensure_data_block(address)
        b0 = self._data_byte(block, offset)
        b1 = self._data_byte(block, offset + 1)
        b2 = self._data_byte(block, offset + 2)
        b3 = self._data_byte(block, offset + 3)
        value = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
        # Sign extension
        if value >= 0x80000000:
            value -= 0x100000000
        return value, latency

    def store_word(self,address,value):
        if address % 4 != 0:
            raise Exception("Address must be 4-byte aligned")
        block_size = self.L1D.block_size
        offset = address % block_size
        val = value & 0xFFFFFFFF
        bytes_list = [
            val & 0xFF,
            (val >> 8) & 0xFF,
            (val >> 16) & 0xFF,
            (val >> 24) & 0xFF
        ]
        if offset + 3 >= block_size:
            latency = 0
            visited_blocks = set()
            for i in range(4):
                addr = address + i
                block_addr = addr - (addr % block_size)
                if block_addr not in visited_blocks:
                    _, lat = self._ensure_data_block(addr)
                    latency += lat
                    visited_blocks.add(block_addr)
                self.L1D.write(addr, bytes_list[i])
                self.L1D.hits-=1
            return latency
        _, latency = self._ensure_data_block(address)
        self.L1D.write(address, bytes_list[0])
        self.L1D.write(address+1, bytes_list[1])
        self.L1D.write(address+2, bytes_list[2])
        self.L1D.write(address+3, bytes_list[3])
        self.L1D.hits -= 4
        return latency

    def load_byte(self,address):
        block, latency = self._ensure_data_block(address)
        offset = address % self.L1D.block_size
        return self._data_byte(block, offset), latency

    def store_byte(self,address,value):
        _, latency = self._ensure_data_block(address)
        self.L1D.write(address,value)
        self.L1D.hits -= 1
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
                    self._insert_l2(base_addr, l.data, dirty=True)
                    l.dirty = False
        for s in self.L2.sets:
            for l in s.lines:
                if l.valid and l.dirty:
                    base_addr = self.L2._reconstruct_address(l.tag, self.L2.sets.index(s))
                    self._write_back(base_addr, l.data)
                    l.dirty = False
        # Drain the Write-Back buffer
        while self.wb_buffer:
             addr, data = self.wb_buffer.pop(0)
             self._actual_write_back(addr, data)
        if self.active_write:
             self._actual_write_back(self.active_write[0], self.active_write[1])
             self.active_write = None
        self.memory_busy_cycles = 0
