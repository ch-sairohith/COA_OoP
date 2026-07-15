class MemoryController:
    def __init__(self, data_memory, memory_latency, max_wb_size=100):
        self.data_memory = data_memory
        self.memory_latency = memory_latency
        self.wb_buffer = []               
        self.MAX_WB_SIZE = max_wb_size
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

    def enqueue_write(self, base_address, data):
        penalty = 0
        if len(self.wb_buffer) >= self.MAX_WB_SIZE:
             if self.memory_busy_cycles > 0:
                 penalty = self.memory_busy_cycles
             else:
                 penalty = self.memory_latency
        self.wb_buffer.append((base_address, list(data)))
        return penalty

    def _actual_write_back(self, base_address, data):
        for i, val in enumerate(data):
            if isinstance(val, int): 
                try:
                    self.data_memory.store_byte(base_address + i, val)
                except Exception:
                    pass

    def flush(self):
        while self.wb_buffer:
             addr, data = self.wb_buffer.pop(0)
             self._actual_write_back(addr, data)
        if self.active_write:
             self._actual_write_back(self.active_write[0], self.active_write[1])
             self.active_write = None
        self.memory_busy_cycles = 0
