class PTEntry:
    """
    One row in the page table.

    vpn   : virtual page number this entry describes
    pfn   : physical frame number it maps to
    valid : True = the page is currently in physical memory
    dirty : True = the page has been written to (needs writeback on eviction)
    """
    def __init__(self, vpn: int, pfn: int):
        self.vpn   = vpn
        self.pfn   = pfn
        self.valid = True
        self.dirty = False


class PageTable:
    """
    Flat (single-level) page table.  Maps VPN -> PTEntry.

    Implemented as a sparse dict so we only store entries for pages
    that have actually been accessed (avoids allocating a huge array
    for the entire virtual address space).

    Methods
    -------
    lookup(vpn)      -> PTEntry | None   (None = page fault)
    insert(vpn, pfn) -> None             (called after page fault)
    set_dirty(vpn)   -> None             (called on store instruction)
    evict(vpn)       -> bool             (True if page was dirty)
    is_dirty(vpn)    -> bool
    """

    def __init__(self, virtual_size_bytes: int, page_size_bytes: int):
        self.num_virtual_pages = virtual_size_bytes // page_size_bytes
        self.table: dict[int, PTEntry] = {}   # VPN -> PTEntry (sparse)

    def lookup(self, vpn: int) -> PTEntry | None:
        """
        Search the page table for a VPN.
        Returns PTEntry if the page is in physical memory.
        Returns None   if the page is not loaded -> PAGE FAULT.
        """
        entry = self.table.get(vpn, None)
        if entry and entry.valid:
            return entry
        return None

    def insert(self, vpn: int, pfn: int):
        """
        Create a new VPN -> PFN mapping.
        Called by PageWalker after a page fault allocates a frame.
        """
        self.table[vpn] = PTEntry(vpn=vpn, pfn=pfn)

    def set_dirty(self, vpn: int):
        """
        Mark a page dirty (it has been written to by a store instruction).
        A dirty page must be written back to swap before its frame is reused.
        """
        entry = self.table.get(vpn)
        if entry:
            entry.dirty = True

    def evict(self, vpn: int) -> bool:
        """
        Remove a VPN mapping (its frame is being reclaimed).
        Returns True if the page was dirty (caller should count dirty_eviction).
        """
        entry = self.table.pop(vpn, None)
        return entry.dirty if entry else False

    def is_dirty(self, vpn: int) -> bool:
        """Check if a page is dirty without removing it (used in tests)."""
        entry = self.table.get(vpn)
        return entry.dirty if entry else False
