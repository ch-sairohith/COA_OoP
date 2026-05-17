"""
vm/test_vm.py
─────────────
Unit tests for the entire VM subsystem.
Run with:  python -m vm.test_vm

Each test prints PASS or FAIL and a short description of what it checks.
"""

import configparser
from vm.address_translator import AddressTranslator


# ── Helper: build a translator with a tiny config ─────────────────────────────

def make_translator(num_frames=4, tlb_entries=2, policy="lru"):
    """
    Creates an AddressTranslator with a minimal config for testing.
    - 4 KB pages
    - 'num_frames' physical frames
    - 'tlb_entries' TLB slots
    """
    cfg = configparser.ConfigParser()
    cfg.read_dict({
        "memory": {
            "virtual_size_bytes" : str(1024 * 1024),   # 1 MB virtual
            "physical_size_bytes": str(num_frames * 4096),
            "page_size_bytes"    : "4096",
        },
        "vm": {
            "dtlb_entries"      : str(tlb_entries),
            "tlb_hit_latency"   : "1",
            "page_walk_latency" : "10",
            "page_fault_latency": "50",
            "replacement_policy": policy,
        },
        "cache": {
            "l1_size_bytes"    : "4096",
            "l1_associativity" : "1",
            "l1_latency"       : "1",
            "l2_enabled"       : "false",
        },
    })
    return AddressTranslator(cfg)


def check(condition, msg):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {msg}")


# ── Test 1: Cold start -> page fault ───────────────────────────────────────────
def test_cold_start():
    print("\nTest 1: Cold start — first access should be a page fault")
    t = make_translator()

    paddr, penalty = t.translate(0x1000)

    check(t.page_faults == 1,    "page_faults = 1")
    check(t.tlb_misses  == 1,    "tlb_misses  = 1")
    check(t.tlb_hits    == 0,    "tlb_hits    = 0")
    # penalty = TLB hit latency(1) + page walk(10) + page fault(50) = 61
    check(penalty == 61,         f"penalty = 61  (got {penalty})")
    # paddr: VPN=1 -> PFN=0 (first frame), offset=0x000
    check(paddr == (0 << 12) | 0x000, f"paddr correct (got {hex(paddr)})")


# ── Test 2: Same address again -> TLB hit ──────────────────────────────────────
def test_tlb_hit():
    print("\nTest 2: Repeated access -> TLB hit")
    t = make_translator()

    t.translate(0x1000)           # cold miss
    paddr, penalty = t.translate(0x1000)   # should be TLB hit

    check(t.tlb_hits   == 1,  "tlb_hits = 1 after second access")
    check(penalty      == 1,  f"penalty = 1 (TLB hit only) (got {penalty})")
    check(t.page_faults == 1, "page_faults still 1 (no new fault)")


# ── Test 3: Different page -> TLB miss + page table hit (no fault) ─────────────
def test_page_table_hit():
    print("\nTest 3: TLB miss but page table hit (TLB entry manually evicted)")
    t = make_translator(tlb_entries=1)  # only 1 TLB slot -> easy to evict

    t.translate(0x1000)  # load VPN=1 -> TLB[0] = VPN 1
    t.translate(0x2000)  # load VPN=2 -> evicts VPN 1 from TLB (only 1 slot)
    # VPN 1 is still in the page table! TLB just doesn't have it.
    paddr, penalty = t.translate(0x1000)

    check(t.page_walks  >= 2, f"at least 2 page walks (got {t.page_walks})")
    check(t.page_faults == 2, f"only 2 page faults total (got {t.page_faults})")
    # Third access to VPN 1: TLB miss + page walk only (no fault) -> 1+10 = 11
    check(penalty == 11,      f"penalty = 11 (walk, no fault) (got {penalty})")


# ── Test 4: Store sets dirty bit ──────────────────────────────────────────────
def test_dirty_tracking():
    print("\nTest 4: Store instruction sets dirty bit")
    t = make_translator()

    t.translate(0x3000, is_write=True)   # VPN = 3, store

    check(t.page_table.is_dirty(3), "page table marks VPN 3 dirty")
    # TLB should also have dirty set
    entry = next((e for e in t.tlb.entries if e.vpn == 3), None)
    check(entry is not None and entry.dirty, "TLB entry for VPN 3 is dirty")


# ── Test 5: Frame eviction when RAM is full ───────────────────────────────────
def test_frame_eviction():
    print("\nTest 5: Fill all frames -> next access causes eviction")
    num_frames = 4
    t = make_translator(num_frames=num_frames, tlb_entries=8)

    # Access 4 different pages -> fills all 4 frames, no eviction yet
    for i in range(num_frames):
        t.translate(i * 0x1000)

    check(t.page_evictions == 0, f"no evictions yet (got {t.page_evictions})")

    # 5th page -> must evict one
    t.translate(num_frames * 0x1000)
    check(t.page_evictions == 1, f"1 eviction after filling RAM (got {t.page_evictions})")


# ── Test 6: Dirty eviction ────────────────────────────────────────────────────
def test_dirty_eviction():
    print("\nTest 6: Evicting a dirty page increments dirty_evictions")
    num_frames = 2
    t = make_translator(num_frames=num_frames, tlb_entries=4)

    t.translate(0x0000, is_write=True)   # VPN 0, dirty
    t.translate(0x1000, is_write=False)  # VPN 1, clean

    # 3rd page -> must evict; LRU = VPN 0 (accessed first, marked dirty)
    t.translate(0x2000)

    check(t.page_evictions >= 1,   f"at least 1 eviction (got {t.page_evictions})")
    check(t.dirty_evictions >= 1,  f"at least 1 dirty eviction (got {t.dirty_evictions})")


# ── Test 7: FIFO policy ───────────────────────────────────────────────────────
def test_fifo_policy():
    print("\nTest 7: FIFO replacement — oldest page is evicted first")
    t = make_translator(num_frames=2, tlb_entries=4, policy="fifo")

    t.translate(0x0000)  # VPN 0 — loaded first (oldest)
    t.translate(0x1000)  # VPN 1 — loaded second
    t.translate(0x0000)  # re-access VPN 0 — FIFO should not update order

    # 3rd unique page -> should evict VPN 0 (oldest in FIFO, even though recently used)
    t.translate(0x2000)
    check(t.page_evictions == 1, f"1 eviction with FIFO (got {t.page_evictions})")


# ── Test 8: Data survives eviction and is restored on re-access ───────────────
def test_swap_restore():
    print("\nTest 8: Data written to a page survives eviction and restore")
    from components.data_mem import Memory

    page_size  = 4096
    num_frames = 2
    data_mem   = Memory(size=num_frames * page_size)  # exactly 2 frames of RAM

    cfg = configparser.ConfigParser()
    cfg.read_dict({
        "memory": {
            "virtual_size_bytes" : str(1024 * 1024),
            "physical_size_bytes": str(num_frames * page_size),
            "page_size_bytes"    : str(page_size),
        },
        "vm": {
            "dtlb_entries"      : "4",
            "tlb_hit_latency"   : "1",
            "page_walk_latency" : "10",
            "page_fault_latency": "50",
            "replacement_policy": "lru",
        },
        "cache": {
            "l1_size_bytes": "4096", "l1_associativity": "1",
            "l1_latency": "1", "l2_enabled": "false",
        },
    })
    t = AddressTranslator(cfg, data_mem=data_mem)

    # Write a known byte to virtual address 0x0005 (VPN=0, offset=5)
    paddr0, _ = t.translate(0x0005, is_write=True)
    data_mem.mem[paddr0] = 0xAB   # write sentinel value

    # Load VPN=1 into the second frame
    t.translate(0x1000)

    # Load VPN=2 — RAM is full (2 frames), LRU evicts VPN=0
    # Eviction should save VPN=0's frame to SecondaryMemory
    t.translate(0x2000)
    check(t.page_evictions == 1, f"1 eviction occurred (got {t.page_evictions})")
    check(t.swap_outs == 1,      f"1 swap_out recorded (got {t.swap_outs})")

    # Re-access VPN=0 — page fault again, but SecondaryMemory restores the data
    paddr0_new, _ = t.translate(0x0005)
    restored_byte = data_mem.mem[paddr0_new]

    check(t.swap_ins == 1,           f"1 swap_in recorded (got {t.swap_ins})")
    check(restored_byte == 0xAB,     f"data restored correctly: got {hex(restored_byte)}")


# ── Run all tests ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("   VM Subsystem Unit Tests")
    print("=" * 55)
    test_cold_start()
    test_tlb_hit()
    test_page_table_hit()
    test_dirty_tracking()
    test_frame_eviction()
    test_dirty_eviction()
    test_fifo_policy()
    test_swap_restore()
    print("\nDone.")
