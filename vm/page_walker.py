from vm.page_table import PageTable
from vm.frame_allocator import FrameAllocator


class PageWalker:
    """
    Handles TLB misses by walking the page table.

    When the TLB doesn't have a VPN → PFN translation, the hardware
    (or OS in a software-managed TLB) must look it up somewhere.
    That "somewhere" is the page table.

    Two outcomes of a page walk
    ---------------------------
    1. PAGE TABLE HIT
       The mapping exists → the page IS in physical memory, the TLB
       just didn't cache it. We return the PFN and charge walk_latency.

    2. PAGE TABLE MISS → PAGE FAULT
       The mapping does NOT exist → the page has NEVER been loaded into
       RAM for this process. We must:
           a) Find a free physical frame (or evict one)
           b) Create a new page table entry
           c) Charge walk_latency + fault_latency

    What PageWalker does NOT do
    ----------------------------
    - It does NOT insert into the TLB (AddressTranslator does that)
    - It does NOT invalidate the TLB (AddressTranslator does that too)
    - It only deals with the page table + frame allocator

    Return value of walk()
    ----------------------
    Always returns a 5-tuple: (pfn, penalty, evicted_vpn, was_dirty_in_pt, was_fault)
    - pfn             : the physical frame number for this VPN
    - penalty         : cycles charged (walk only, or walk + fault)
    - evicted_vpn     : the VPN that was kicked out of RAM (None if no eviction)
    - was_dirty_in_pt : True if the evicted page was dirty in the Page Table
    - was_fault       : True if the page was missing from RAM (Page Fault)
    """

    def __init__(self, page_table: PageTable, frame_allocator: FrameAllocator,
                 walk_latency: int, fault_latency: int):
        self.page_table      = page_table
        self.frame_allocator = frame_allocator
        self.walk_latency    = walk_latency
        self.fault_latency   = fault_latency

        # Stats (exposed via AddressTranslator properties)
        self.page_walks  = 0
        self.page_faults = 0

    def walk(self, vpn: int) -> tuple:
        """
        Walk the page table for the given VPN.

        Called by AddressTranslator on every TLB miss.

        Returns: (pfn, penalty, evicted_vpn, was_dirty_in_pt, was_fault)
        """
        self.page_walks += 1
        penalty      = self.walk_latency
        evicted_vpn  = None

        # ---- Step 1: Check the page table ----
        entry = self.page_table.lookup(vpn)

        if entry is not None:
            # Page table HIT - the page is in RAM, just not in TLB
            return entry.pfn, penalty, None, False, False

        # ---- Step 2: Page Fault — page not in RAM ----
        self.page_faults += 1
        penalty += self.fault_latency

        # Ask FrameAllocator for a physical frame
        # It may need to evict another page if RAM is full
        frame_id, evicted_vpn = self.frame_allocator.allocate(vpn)

        was_dirty_in_pt = False
        if evicted_vpn is not None:
            # A page was kicked out to make room
            # Remove its page table entry (AddressTranslator will handle TLB)
            was_dirty_in_pt = self.page_table.evict(evicted_vpn)

        # Create the new page table entry for our VPN
        self.page_table.insert(vpn, frame_id)

        return frame_id, penalty, evicted_vpn, was_dirty_in_pt, True
