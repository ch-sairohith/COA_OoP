from collections import deque


class Frame:
    """
    Represents one physical frame (page-sized chunk of RAM).

    Fields
    ------
    frame_id : unique number 0..N-1
    vpn      : which virtual page currently lives in this frame (None = free)
    dirty    : True if the page in this frame has been written to
    """
    def __init__(self, frame_id: int):
        self.frame_id = frame_id
        self.vpn      = None    # free initially
        self.dirty    = False


class FrameAllocator:
    """
    Manages the pool of physical frames.

    Think of this as the RAM manager. The OS uses it to:
    - Hand out free frames when a new page is needed (page fault)
    - Decide which frame to steal (evict) when RAM is full
    - Track which frames are dirty (need writeback)

    Replacement Policies
    --------------------
    LRU  : evict the frame that was used least recently
    FIFO : evict the frame that was loaded the longest ago (oldest)

    Responsibilities
    ----------------
    allocate(vpn)         → give a frame to this VPN; may evict another
    mark_accessed(fid)    → update LRU order on TLB hit
    mark_dirty(fid)       → frame has been written to
    get_frame_for_vpn(v)  → find which frame a VPN occupies
    """

    def __init__(self, num_frames: int, replacement_policy: str):
        self.num_frames          = num_frames
        self.replacement_policy  = replacement_policy.lower()

        # All frames, indexed by frame_id
        self.frames: list[Frame] = [Frame(i) for i in range(num_frames)]

        # List of frame_ids that are currently free (no page loaded)
        self.free_list: list[int] = list(range(num_frames))

        # LRU: list of frame_ids of occupied frames
        # leftmost = least recently used, rightmost = most recently used
        self._lru_order: list[int] = []

        # FIFO: deque of frame_ids of occupied frames (oldest at left)
        self._fifo_queue: deque = deque()

        # Performance counters
        self.evictions       = 0   # total frames evicted
        self.dirty_evictions = 0   # evictions where the page was dirty

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allocate(self, vpn: int) -> tuple:
        """
        Give a physical frame to the virtual page `vpn`.

        Returns
        -------
        (frame_id, evicted_vpn, was_dirty)

        - frame_id    : the frame number assigned to this VPN
        - evicted_vpn : the VPN that was kicked out (None if a free frame existed)
        - was_dirty   : True if the evicted page was dirty (needs writeback)

        The caller (PageWalker) MUST:
        1. Remove evicted_vpn from the page table   (PageTable.evict)
        2. Remove evicted_vpn from the TLB          (TLB.invalidate)
        """
        if self.free_list:
            # ---- Easy case: free frame available ----
            frame_id = self.free_list.pop(0)
            self.frames[frame_id].vpn   = vpn
            self.frames[frame_id].dirty = False
            self._track_insert(frame_id)
            return frame_id, None, False

        # ---- Hard case: RAM is full, must evict ----
        frame_id     = self._choose_victim()
        victim_frame = self.frames[frame_id]

        evicted_vpn = victim_frame.vpn
        was_dirty   = victim_frame.dirty

        self.evictions += 1
        if was_dirty:
            self.dirty_evictions += 1

        # Overwrite the frame with the new VPN
        victim_frame.vpn   = vpn
        victim_frame.dirty = False
        self._track_insert(frame_id)

        return frame_id, evicted_vpn, was_dirty

    def mark_accessed(self, frame_id: int):
        """
        Tell the allocator this frame was just used.
        Only matters for LRU — moves it to the MRU end so it won't
        be evicted soon.
        Called by AddressTranslator on every TLB hit.
        """
        if self.replacement_policy == "lru":
            if frame_id in self._lru_order:
                self._lru_order.remove(frame_id)
            self._lru_order.append(frame_id)

    def mark_dirty(self, frame_id: int):
        """
        Mark a frame as dirty (a store instruction modified the page in it).
        """
        self.frames[frame_id].dirty = True

    def get_frame_for_vpn(self, vpn: int) -> int | None:
        """
        Find which frame_id currently holds a given VPN.
        Returns None if the VPN is not in any frame (shouldn't happen
        after a successful translate, but useful for safety).
        """
        for frame in self.frames:
            if frame.vpn == vpn:
                return frame.frame_id
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _choose_victim(self) -> int:
        """Pick a frame to evict based on the replacement policy."""
        if self.replacement_policy == "lru":
            return self._lru_order.pop(0)    # leftmost = LRU
        else:
            return self._fifo_queue.popleft() # oldest inserted

    def _track_insert(self, frame_id: int):
        """Record that frame_id is now occupied / recently used."""
        if self.replacement_policy == "lru":
            if frame_id in self._lru_order:
                self._lru_order.remove(frame_id)
            self._lru_order.append(frame_id)
        else:  # fifo
            if frame_id in self._fifo_queue:
                self._fifo_queue.remove(frame_id)
            self._fifo_queue.append(frame_id)
