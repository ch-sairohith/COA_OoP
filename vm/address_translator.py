import configparser

from vm.tlb              import TLB
from vm.page_table       import PageTable
from vm.frame_allocator  import FrameAllocator
from vm.page_walker      import PageWalker
from vm.secondary_memory import SecondaryMemory


class AddressTranslator:
    """
    THE BOSS — orchestrates the entire VM subsystem.

    The ONLY method Person B ever calls:
        paddr, penalty = translator.translate(vaddr, is_write=False)

    How translate() works (step by step):
    ──────────────────────────────────────
    1. Split vaddr into VPN (which page) + offset (where inside the page)
    2. Ask TLB: "do you have VPN -> PFN?"
         HIT  -> use that PFN directly. Charge tlb_hit_latency cycles.
         MISS -> ask PageWalker.walk(VPN):
                   - If page is in page table (just not in TLB):
                       return PFN, charge walk_latency
                   - If page is NOT in page table (page fault):
                       allocate a frame (evict if RAM full),
                       charge walk_latency + fault_latency
    3. If a frame was evicted during a page fault:
         a) Save that frame's bytes to SecondaryMemory (swap)
         b) Invalidate the evicted VPN from the TLB
         Then, for the new VPN:
         c) If it was in swap -> restore its bytes to the new frame
         d) If it's brand new -> zero out the new frame
    4. Insert the new VPN->PFN into TLB
    5. If this is a store (is_write=True): mark the page dirty
    6. Build paddr = (PFN << offset_bits) | offset
    7. Return (paddr, total penalty cycles)
    """

    def __init__(self, config: configparser.ConfigParser, data_mem=None):
        """
        Parameters
        ----------
        config   : ConfigParser object loaded from config_vm.ini
        data_mem : Memory object (components/data_mem.py).
                   Required for swap save/restore (data correctness).
                   If None, only stats are tracked (no byte-level swap).
        """
        # ── Read all config values ─────────────────────────────────────
        page_size  = config.getint("memory", "page_size_bytes")
        virt_size  = config.getint("memory", "virtual_size_bytes")
        phys_size  = config.getint("memory", "physical_size_bytes")
        num_frames = phys_size // page_size
        policy     = config.get("vm", "replacement_policy").lower()

        tlb_entries = config.getint("vm", "dtlb_entries")
        tlb_hit_lat = config.getint("vm", "tlb_hit_latency")
        walk_lat    = config.getint("vm", "page_walk_latency")
        fault_lat   = config.getint("vm", "page_fault_latency")

        # ── How to split a virtual address ────────────────────────────
        # For 4 KB pages: offset_bits = 12,  offset_mask = 0xFFF
        # vaddr >> 12        gives VPN    (which page)
        # vaddr &  0xFFF     gives offset (byte position inside page)
        self.page_size   = page_size
        self.offset_bits = page_size.bit_length() - 1
        self.offset_mask = page_size - 1

        # ── Build all sub-components ───────────────────────────────────
        self.tlb = TLB(
            num_entries        = tlb_entries,
            hit_latency        = tlb_hit_lat,
            replacement_policy = policy
        )
        self.page_table = PageTable(virt_size, page_size)
        self.frame_allocator = FrameAllocator(num_frames, policy)
        self.page_walker = PageWalker(
            page_table      = self.page_table,
            frame_allocator = self.frame_allocator,
            walk_latency    = walk_lat,
            fault_latency   = fault_lat
        )

        # swap: simulates disk storage for evicted pages
        self.data_mem      = data_mem           # actual physical RAM bytes
        self.secondary_mem = SecondaryMemory(page_size)  # simulated disk

        # Running total of all VM-related stall cycles
        self.total_penalty_cycles = 0

    # ──────────────────────────────────────────────────────────────────
    # Public API (Person B calls this)
    # ──────────────────────────────────────────────────────────────────

    def translate(self, vaddr: int, is_write: bool = False) -> tuple:
        """
        Translate a virtual address to a physical address.

        Parameters
        ----------
        vaddr    : virtual address from trace (e.g. 0x1ABC)
        is_write : True for S (store), False for L (load)

        Returns
        -------
        (paddr, penalty_cycles)
        """

        # Step 1: Split address
        vpn    = vaddr >> self.offset_bits   # which virtual page
        offset = vaddr & self.offset_mask    # byte position inside that page
        penalty = 0

        # Step 2: TLB lookup
        # Always charge tlb_hit_latency (hardware checks TLB on every access)
        penalty += self.tlb.hit_latency
        pfn = self.tlb.lookup(vpn)

        if pfn is not None:
            # ── TLB HIT: translation found in TLB ────────────────────
            # Update LRU order in FrameAllocator so this frame stays "recent"
            frame_id = self.frame_allocator.get_frame_for_vpn(vpn)
            if frame_id is not None:
                self.frame_allocator.mark_accessed(frame_id)

        else:
            # ── TLB MISS: must walk the page table ───────────────────
            pfn, walk_penalty, evicted_vpn = self.page_walker.walk(vpn)
            penalty += walk_penalty

            # page_walker.walk() returns evicted_vpn != None ONLY when
            # a page fault occurred AND a frame had to be evicted.
            # If it was just a page table hit (no fault), evicted_vpn = None.

            # was_fault = True means walk() had to allocate a new frame
            # (i.e. vpn was not in the page table — a page fault happened)
            was_fault = (walk_penalty > self.page_walker.walk_latency)

            if was_fault and self.data_mem is not None:
                # Step 3a: Save evicted frame's bytes to swap (before reuse)
                if evicted_vpn is not None:
                    self._save_frame_to_swap(evicted_vpn, pfn)
                    self.tlb.invalidate(evicted_vpn)

                # Step 3b: Prepare the new frame for vpn
                #   - if vpn was previously evicted: restore from swap
                #   - if vpn is brand new: zero out the frame
                self._prepare_frame_for_vpn(vpn, pfn)

            elif evicted_vpn is not None:
                # No data_mem provided (stats-only mode):
                # Still need to invalidate the stale TLB entry
                self.tlb.invalidate(evicted_vpn)

            # Step 4: Cache the new translation in TLB
            self.tlb.insert(vpn, pfn)

        # Step 5: Mark dirty on store instructions
        if is_write:
            self._mark_dirty(vpn)

        # Step 6: Build and return physical address
        paddr = (pfn << self.offset_bits) | offset
        self.total_penalty_cycles += penalty
        return paddr, penalty

    # ──────────────────────────────────────────────────────────────────
    # Private helpers (called only by translate())
    # ──────────────────────────────────────────────────────────────────

    def _save_frame_to_swap(self, evicted_vpn: int, pfn: int):
        """
        Before frame `pfn` is given to a new VPN, save its current
        byte content to SecondaryMemory under the key `evicted_vpn`.
        This way, if evicted_vpn is accessed again later, we can restore it.
        """
        frame_start = pfn * self.page_size
        frame_end   = min(frame_start + self.page_size, len(self.data_mem.mem))
        page_bytes  = bytes(self.data_mem.mem[frame_start:frame_end])
        self.secondary_mem.save(evicted_vpn, page_bytes)

    def _prepare_frame_for_vpn(self, vpn: int, pfn: int):
        """
        Set up frame `pfn` for incoming VPN `vpn`:
        - If vpn was previously evicted (exists in swap): restore its bytes.
        - If vpn is brand new (first ever access): zero out the frame.
        """
        frame_start = pfn * self.page_size
        frame_end   = min(frame_start + self.page_size, len(self.data_mem.mem))
        length      = frame_end - frame_start

        if self.secondary_mem.has_page(vpn):
            # Previously evicted page coming back — restore its saved bytes
            saved_bytes = self.secondary_mem.restore(vpn)
            self.data_mem.mem[frame_start:frame_end] = saved_bytes[:length]
        else:
            # Brand new page — fill frame with zeros
            self.data_mem.mem[frame_start:frame_end] = bytearray(length)

    def _mark_dirty(self, vpn: int):
        """
        Mark a page as dirty in all three places that track it:
        1. PageTable  - authoritative source of truth
        2. TLB entry  - so TLB-level checks also see the dirty bit
        3. Frame      - so FrameAllocator counts dirty evictions correctly
        """
        self.page_table.set_dirty(vpn)
        self.tlb.set_dirty(vpn)
        frame_id = self.frame_allocator.get_frame_for_vpn(vpn)
        if frame_id is not None:
            self.frame_allocator.mark_dirty(frame_id)

    # ──────────────────────────────────────────────────────────────────
    # Stats (Person B reads these for the final report)
    # ──────────────────────────────────────────────────────────────────

    @property
    def tlb_hits(self):           return self.tlb.hits
    @property
    def tlb_misses(self):         return self.tlb.misses
    @property
    def page_walks(self):         return self.page_walker.page_walks
    @property
    def page_faults(self):        return self.page_walker.page_faults
    @property
    def page_evictions(self):     return self.frame_allocator.evictions
    @property
    def dirty_evictions(self):    return self.frame_allocator.dirty_evictions
    @property
    def swap_outs(self):          return self.secondary_mem.swap_outs
    @property
    def swap_ins(self):           return self.secondary_mem.swap_ins
