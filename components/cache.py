class CacheLine:
    def __init__(self, block_size):
        self.valid = False
        self.dirty = False
        self.tag = None
        self.data = [None] * block_size

class CacheSet:
    def __init__(self, associativity, block_size):
        self.lines = []
        for i in range(associativity):
            self.lines.append(CacheLine(block_size))
        self.lru_order = []  # left = least recent

class Cache:
    def __init__(self, cache_size, block_size, associativity, latency, replacement_policy="LRU"):
        self.cache_size = cache_size
        self.block_size = block_size
        self.associativity = associativity
        self.latency = latency
        self.replacement_policy = replacement_policy
        self.num_sets = cache_size // (block_size * associativity)
        self.sets = []
        for _ in range(self.num_sets):
            self.sets.append(CacheSet(associativity, block_size))
        self.hits = 0
        self.misses = 0

    def _get_index_tag_offset(self, address):
        offset_bits = self.block_size.bit_length() - 1
        index_bits = self.num_sets.bit_length() - 1
        offset = address & ((1 << offset_bits) - 1)
        block_number = address >> offset_bits
        index = block_number & ((1 << index_bits) - 1)
        tag = block_number >> index_bits
        return index, tag, offset

    def read(self, address):
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        i = 0
        while i < len(cache_set.lines):
            line = cache_set.lines[i]
            if line.valid and line.tag == tag:
                self.hits += 1
                if i in cache_set.lru_order:
                    cache_set.lru_order.remove(i)
                cache_set.lru_order.append(i)
                return (True,line.data[offset])
            i += 1
        self.misses += 1
        return (False,None)

    def write(self, address, value):
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        i = 0
        while i < len(cache_set.lines):
            line = cache_set.lines[i]
            if line.valid and line.tag == tag:
                self.hits += 1
                line.data[offset] = value
                line.dirty = True
                if i in cache_set.lru_order:
                    cache_set.lru_order.remove(i)
                cache_set.lru_order.append(i)
                return True
            i += 1
        self.misses += 1
        return False

    def insert(self, address, block_data, dirty=False):
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        i = 0
        while i < len(cache_set.lines):
            line = cache_set.lines[i]
            if line.valid and line.tag == tag:
                line.data = list(block_data)
                line.dirty = dirty
                if i in cache_set.lru_order:
                    cache_set.lru_order.remove(i)
                cache_set.lru_order.append(i)
                return None
            i += 1
            
        i = 0
        while i < len(cache_set.lines):
            line = cache_set.lines[i]
            if not line.valid:
                line.valid = True
                line.tag = tag
                line.dirty = dirty
                line.data = list(block_data) 
                if i in cache_set.lru_order:
                    cache_set.lru_order.remove(i)
                cache_set.lru_order.append(i)
                return None
            i += 1
        # -------- 2. Eviction (LRU) since set is full --------
        lru_index = cache_set.lru_order.pop(0)
        evict_line = cache_set.lines[lru_index]
        write_back_info = None
        if evict_line.dirty:
            base_address = self._reconstruct_address(evict_line.tag, index)
            write_back_info = (base_address, evict_line.data)
        evict_line.valid = True
        evict_line.tag = tag
        evict_line.dirty = dirty
        evict_line.data = list(block_data) 
        cache_set.lru_order.append(lru_index)
        return write_back_info
    
    def _reconstruct_address(self, tag, index):
        offset_bits = self.block_size.bit_length() - 1
        index_bits = self.num_sets.bit_length() - 1
        block_number = (tag << index_bits) | index
        base_address = block_number << offset_bits
        return base_address