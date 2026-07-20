class TLBEntry:
    """
    Represents one slot inside the TLB.
    Each entry remembers which virtual page (VPN) it is caching
    and what physical frame (PFN) it maps to.
    """
    def __init__(self, vpn: int, pfn: int):
        self.vpn   = vpn
        self.pfn   = pfn
        self.valid = True
        self.dirty = False   # set to True when a store touches this page


class TLB:
    """
    Data TLB (DTLB).

    Responsibilities
    ----------------
    - Cache recent VPN → PFN translations so we don't have to walk
      the page table on every memory access.
    - Track hit / miss counts for the final report.
    - Evict the least-recently-used (LRU) entry when the TLB is full
      and we need to add a new one.

    How it fits in the big picture
    --------------------------------
    AddressTranslator calls:
        pfn = tlb.lookup(vpn)   → None means miss
        tlb.insert(vpn, pfn)    → after every miss, once PFN is found
        tlb.invalidate(vpn)     → when a physical frame is evicted
        tlb.set_dirty(vpn)      → on every store instruction
    """

    def __init__(self, num_entries: int, hit_latency: int):
        self.num_entries         = num_entries
        self.hit_latency         = hit_latency          # cycles charged on every access 
        # We accept replacement_policy to avoid breaking config calls, but TLB only uses LRU.
        
        # The actual TLB storage: a list of TLBEntry objects
        self.entries: list[TLBEntry] = []

        # LRU tracking: list of indices into self.entries
        # leftmost index = least recently used, rightmost = most recently used
        self._lru_order: list[int] = []

        # Performance counters (read by AddressTranslator for the report)
        self.hits   = 0
        self.misses = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(self, vpn: int) -> int | None:
        """
        Search the TLB for a VPN.

        Returns
        -------
        PFN (int)  if found (TLB hit)
        None       if not found (TLB miss)

        Side effects
        ------------
        - Increments self.hits or self.misses
        - On a hit, moves the entry to the MRU position (for LRU policy)
        """
        for idx, entry in enumerate(self.entries):
            if entry.valid and entry.vpn == vpn:
                # ---- HIT ----
                self.hits += 1
                self._update_lru(idx)
                return entry.pfn

        # ---- MISS ----
        self.misses += 1
        return None

    def insert(self, vpn: int, pfn: int) -> tuple[int, bool] | None:
        """
        Add a new VPN → PFN mapping into the TLB.

        If the TLB is not full, just append.
        If the TLB is full, evict the LRU entry first,
        then overwrite that slot and return (evicted_vpn, was_dirty).
        """
        # Check if VPN already exists (update in place)
        for idx, entry in enumerate(self.entries):
            if entry.vpn == vpn:
                entry.pfn   = pfn
                entry.valid = True
                entry.dirty = False
                self._update_lru(idx)
                return None

        if len(self.entries) < self.num_entries:
            # Free slot available — just append
            new_idx = len(self.entries)
            self.entries.append(TLBEntry(vpn, pfn))
            self._update_lru(new_idx)
            return None
        else:
            # TLB is full — must evict
            evict_idx = self._choose_victim()
            evicted_vpn = self.entries[evict_idx].vpn
            was_dirty   = self.entries[evict_idx].dirty
            
            self.entries[evict_idx].vpn   = vpn
            self.entries[evict_idx].pfn   = pfn
            self.entries[evict_idx].valid = True
            self.entries[evict_idx].dirty = False
            self._update_lru(evict_idx)
            return (evicted_vpn, was_dirty)

    def set_dirty(self, vpn: int):
        """
        Mark a TLB entry as dirty.
        Called by AddressTranslator every time a store (S) instruction
        touches a page, so we know the page has been written to.
        """
        for entry in self.entries:
            if entry.valid and entry.vpn == vpn:
                entry.dirty = True
                return

    def invalidate(self, vpn: int) -> bool:
        """
        Remove a VPN from the TLB and return its dirty status.
        Called when a physical frame is evicted — we must not leave
        a stale entry sitting in the TLB. We return the dirty status
        so the AddressTranslator can perform a write-back if needed.
        """
        for idx, entry in enumerate(self.entries):
            if entry.valid and entry.vpn == vpn:
                entry.valid = False
                was_dirty = entry.dirty
                # Remove from tracking structures
                if idx in self._lru_order:
                    self._lru_order.remove(idx)
                return was_dirty
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_lru(self, idx: int):
        """Update LRU order when an entry is accessed or inserted."""
        if idx in self._lru_order:
            self._lru_order.remove(idx)
        self._lru_order.append(idx)   # move to MRU end

    def _choose_victim(self) -> int:
        """Return the index of the entry to evict (LRU)."""
        return self._lru_order.pop(0)   # leftmost = least recently used
