from collections import deque


class Frame:
    """
    Represents one physical frame (page-sized chunk of RAM).

    Fields
    ------
    frame_id : unique number 0..N-1
    vpn      : which virtual page currently lives in this frame (None = free)
    """
    def __init__(self, frame_id: int):
        self.frame_id = frame_id
        self.vpn      = None    # free initially


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

    Responsibilities
    ----------------
    allocate(vpn)         → give a frame to this VPN; may evict another
    mark_accessed(fid)    → update LRU order on TLB hit
    """

    def __init__(self, num_frames: int):
        self.num_frames          = num_frames
        # All frames, indexed by frame_id
        self.frames: list[Frame] = [Frame(i) for i in range(num_frames)]
        
        # List of frame_ids that are currently free (no page loaded)
        # We reserve Frame 0 (0x0000 - 0x0FFF) exclusively for Instruction Memory
        # so the OS never hands it out to Data Memory, preventing L2 Cache collisions!
        start_frame = 1 if num_frames > 1 else 0
        self.free_list: list[int] = list(range(start_frame, num_frames))

        # LRU: list of frame_ids of occupied frames
        # leftmost = least recently used, rightmost = most recently used
        self._lru_order: list[int] = []

        # Performance counters
        self.evictions       = 0   # total frames evicted
        self.dirty_evictions = 0   # evictions where the page was dirty

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allocate(self, vpn: int) -> tuple[int, int | None]:
        """
        Give a physical frame to the virtual page `vpn`.

        Returns
        -------
        (frame_id, evicted_vpn)

        - frame_id    : the frame number assigned to this VPN
        - evicted_vpn : the VPN that was kicked out (None if a free frame existed)

        The caller (PageWalker) MUST:
        1. Remove evicted_vpn from the page table   (PageTable.evict)
        2. Remove evicted_vpn from the TLB          (TLB.invalidate)
        """
        if self.free_list:
            # ---- Easy case: free frame available ----
            frame_id = self.free_list.pop(0)
            self.frames[frame_id].vpn = vpn
            self._track_insert(frame_id)
            return frame_id, None

        # ---- Hard case: RAM is full, must evict ----
        frame_id     = self._choose_victim()
        victim_frame = self.frames[frame_id]

        evicted_vpn = victim_frame.vpn

        self.evictions += 1

        # Overwrite the frame with the new VPN
        victim_frame.vpn = vpn
        self._track_insert(frame_id)

        return frame_id, evicted_vpn

    def mark_accessed(self, frame_id: int):
        """
        Tell the allocator this frame was just used.
        Moves it to the MRU end so it won't be evicted soon.
        Called by AddressTranslator on every TLB hit.
        """
        if frame_id in self._lru_order:
            self._lru_order.remove(frame_id)
        self._lru_order.append(frame_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _choose_victim(self) -> int:
        """Pick a frame to evict (LRU)."""
        return self._lru_order.pop(0)    # leftmost = LRU

    def _track_insert(self, frame_id: int):
        """Record that frame_id is now occupied / recently used."""
        if frame_id in self._lru_order:
            self._lru_order.remove(frame_id)
        self._lru_order.append(frame_id)
