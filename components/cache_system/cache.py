from abc import ABC, abstractmethod

class EvictionPolicy(ABC):
    @abstractmethod
    def on_access(self, cache_set, index):
        pass
    
    @abstractmethod
    def on_insert(self, cache_set, index):
        pass

    @abstractmethod
    def get_victim(self, cache_set):
        pass

class LRUPolicy(EvictionPolicy):
    def on_access(self, cache_set, index):
        if index in cache_set.lru_order:
            cache_set.lru_order.remove(index)
        cache_set.lru_order.append(index)
        
    def on_insert(self, cache_set, index):
        self.on_access(cache_set, index)
        
    def get_victim(self, cache_set):
        return cache_set.lru_order[0]

class LFUPolicy(EvictionPolicy):
    def on_access(self, cache_set, index):
        cache_set.access_counts[index] += 1
        if index in cache_set.lru_order:
            cache_set.lru_order.remove(index)
        cache_set.lru_order.append(index)
        
    def on_insert(self, cache_set, index):
        cache_set.access_counts[index] = 1
        if index in cache_set.lru_order:
            cache_set.lru_order.remove(index)
        cache_set.lru_order.append(index)
        
    def get_victim(self, cache_set):
        min_access = float('inf')
        candidates = []
        for i, count in enumerate(cache_set.access_counts):
            if cache_set.lines[i].valid:
                if count < min_access:
                    min_access = count
                    candidates = [i]
                elif count == min_access:
                    candidates.append(i)
        
        # Tie breaker LRU
        for idx in cache_set.lru_order:
            if idx in candidates:
                return idx
        return candidates[0]

class CacheLine:
    def __init__(self, block_size):
        self.valid = False
        self.dirty = False
        self.tag = None
        self.data = [None] * block_size

class CacheSet:
    def __init__(self, associativity, block_size, policy):
        self.lines = [CacheLine(block_size) for _ in range(associativity)]
        self.lru_order = []
        self.access_counts = [0] * associativity
        self.policy = policy
        
    def find_line(self, tag):
        for i, line in enumerate(self.lines):
            if line.valid and line.tag == tag:
                return i, line
        return -1, None
        
    def get_empty_slot(self):
        for i, line in enumerate(self.lines):
            if not line.valid:
                return i
        return -1
        
    def access(self, index):
        self.policy.on_access(self, index)
        
    def update(self, index, data, dirty=False):
        line = self.lines[index]
        line.dirty = dirty
        line.data = list(data)
        self.policy.on_access(self, index)
        
    def insert(self, index, tag, data, dirty=False):
        line = self.lines[index]
        line.valid = True
        line.tag = tag
        line.dirty = dirty
        line.data = list(data)
        self.policy.on_insert(self, index)
        
    def evict(self):
        return self.policy.get_victim(self)

class Cache:
    def __init__(self, cache_size, block_size, associativity, latency, replacement_policy="LRU"):
        self.cache_size = cache_size
        self.block_size = block_size
        self.associativity = associativity
        self.latency = latency
        self.replacement_policy = replacement_policy
        
        if replacement_policy == "LFU":
            self.policy = LFUPolicy()
        else:
            self.policy = LRUPolicy()
            
        self.num_sets = cache_size // (block_size * associativity)
        self.sets = [CacheSet(associativity, block_size, self.policy) for _ in range(self.num_sets)]
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

    def _reconstruct_address(self, tag, index):
        offset_bits = self.block_size.bit_length() - 1
        index_bits = self.num_sets.bit_length() - 1
        block_number = (tag << index_bits) | index
        base_address = block_number << offset_bits
        return base_address

    def read(self, address): # it reads one element in the cache block 
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        line_idx, line = cache_set.find_line(tag)
        if line:
            self.hits += 1
            cache_set.access(line_idx)
            return (True, line.data[offset])
        self.misses += 1
        return (False, None)

    def read_block(self, address, update_stats=False):
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        line_idx, line = cache_set.find_line(tag)
        if line:
            if update_stats:
                self.hits += 1
                cache_set.access(line_idx)
            return line.data
        if update_stats:
            self.misses += 1
        return None

    def write(self, address, value):
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        line_idx, line = cache_set.find_line(tag)
        if line:
            line.data[offset] = value
            line.dirty = True
            return True
        return False

    def insert(self, address, block_data, dirty=False):
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        
        line_idx, line = cache_set.find_line(tag)
        if line:
            cache_set.update(line_idx, block_data, dirty)
            return None
            
        empty_idx = cache_set.get_empty_slot()
        if empty_idx != -1:
            cache_set.insert(empty_idx, tag, block_data, dirty)
            return None
            
        evict_idx = cache_set.evict()
        evict_line = cache_set.lines[evict_idx]
        evicted_base_address = self._reconstruct_address(evict_line.tag, index)
        evicted_info = (evicted_base_address, list(evict_line.data), evict_line.dirty)
        
        cache_set.insert(evict_idx, tag, block_data, dirty)
        return evicted_info

    def invalidate(self, address):
        index, tag, offset = self._get_index_tag_offset(address)
        cache_set = self.sets[index]
        line_idx, line = cache_set.find_line(tag)
        if line:
            line.valid = False
            if line_idx in cache_set.lru_order:
                cache_set.lru_order.remove(line_idx)
            if line.dirty:
                base_address = self._reconstruct_address(tag, index)
                return (base_address, list(line.data))
        return None