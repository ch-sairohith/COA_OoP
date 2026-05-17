# RISC-V Pipelined Processor Simulator

A Python-based simulation of a 5-stage pipelined RISC-V processor with a two-level cache hierarchy.

## What This Is

This simulator models a classic 5-stage RISC-V pipeline:

```
IF → ID → EX → MEM → WB
```

It supports data forwarding, stall detection, early branch resolution, a full two-level cache hierarchy (L1I, L1D, L2), and a complete Virtual Memory subsystem. We also wrote an assembler/parser so you can write actual `.asm` files and run them through the simulator, or parse trace files for testing.

## How to Run

> Make sure you have Python 3 installed.

### Standard Mode
1. Write your assembly program in `program.asm`
2. Run:
   ```bash
   python main.py
   ```
3. The simulator prints final register state, non-zero memory, stall breakdown, IPC, and cache miss rates.

### Trace Mode (Virtual Memory Testing)
To execute a trace file containing memory operations (like `test_trace.trc`), run:
```bash
python main.py --trace test_trace.trc
```
This mode also prints detailed Virtual Memory statistics (TLB hits/misses, page faults, swap operations, etc.).

## Features

### Phase 1 — Pipeline
- **5-stage pipeline** — Fetch, Decode, Execute, Memory, Writeback
- **Data forwarding** — EX-to-EX, MEM-to-EX, MEM-to-ID and EX-to-ID forwarding to minimize stalls
- **Hazard detection** — Handles load-use stalls, data hazards, and branch hazards
- **Early branch resolution** — Branches are resolved in the Decode stage (1-cycle penalty only)
- **Configurable** — Forwarding can be turned on/off via `config.json`
- **Custom assembler** — Parses a subset of RISC-V assembly directly

### Phase 2 — Cache Hierarchy
- **Two-level cache** — Separate L1 instruction (L1I) and data (L1D) caches, plus a unified L2 cache
- **Two replacement policies** — LRU (Least Recently Used) and LFU (Least Frequently Used); configurable per cache level
- **Variable memory latency** — Both IF and MEM stages stall based on actual cache hit/miss latency
- **Store buffer** — Stores are buffered so the pipeline sees 1-cycle write latency; background drain handles actual cache writes
- **Store-to-load forwarding** — Loads that hit an in-flight store in the store buffer get the data without going to cache
- **Write-back + inclusion policy** — Dirty evictions from L1 are written back through L2; evicting a block from L2 also invalidates it in L1
- **Cache statistics** — Miss rate reported per cache level (L1I, L1D, L2) at end of execution

### Phase 3 — Virtual Memory Subsystem
- **Virtual to Physical Translation** — Address translation seamlessly integrated into the memory stage (MEM).
- **TLB & Hardware Page Walker** — Supports fast address translation through TLB and multi-level page table walking on misses.
- **Demand Paging** — Frame allocator and secondary memory structures to simulate page faults and swap-ins.
- **Trace-based Execution** — Capable of reading and executing instruction trace files (`test_trace.trc`) for intensive memory and translation testing.
- **Multi-cycle Execution Latencies** — Pipeline stall logic in the EX stage extended to support multi-cycle instructions like `mul`.


## Supported Instructions

| Type | Instructions |
|------|-------------|
| R-type | `add`, `sub`, `slt`, `mul` |
| I-type | `addi`, `lw` |
| S-type | `sw` |
| B-type | `beq`, `bne` |
| J-type | `jal` |
| Pseudo | `la`, `j` |

## Project Structure

```
COA_OoP/
├── main.py                  # Entry point — run this
├── program.asm              # Assembly program to simulate
├── test_trace.trc           # Trace file with operations for testing
├── config.json              # Cache + pipeline configuration
├── config_vm.ini            # Virtual memory configuration
│
├── core/
│   ├── simulator.py         # Main simulation loop
│   ├── hazard_unit.py       # Forwarding + stall logic
│   └── latches.py           # Pipeline latch dataclasses
│
├── stages/
│   ├── fetch.py             # IF stage (with I-cache miss handling)
│   ├── decode.py            # ID stage (+ early branch resolution)
│   ├── execute.py           # EX stage
│   ├── mem.py               # MEM stage (store buffer + D-cache access)
│   └── writeback.py         # WB stage
│
├── components/
│   ├── register.py          # 32 general-purpose registers (x0–x31)
│   ├── data_mem.py          # Byte-addressable data memory (4 KB)
│   ├── Instruction_mem.py   # Instruction memory
│   ├── cache.py             # Generic cache (LRU / LFU, set-associative)
│   └── cache_hierarchy.py   # L1I + L1D + L2 hierarchy with eviction logic
│
├── utils/
│   ├── parser.py            # Assembles .asm → Instruction objects
│   └── Instruction.py       # Instruction dataclass
│
└── vm/                      # Phase 3 Virtual Memory subsystem
    ├── address_translator.py# Core VA-to-PA translation logic
    ├── frame_allocator.py   # Physical frame management
    ├── page_table.py        # Page table entry structures
    ├── page_walker.py       # Hardware page table walker
    ├── tlb.py               # Translation Lookaside Buffer
    └── secondary_memory.py  # Disk/Swap storage model
```


## Configuration

Edit `config.json` to change simulator behaviour:

```json
{
  "forwarding_enabled": true,
  "latencies": {
    "lw": 3,
    "sw": 2,
    "add": 4
  },
  "MEMORY_LATENCY": 50,
  "L1I": {
    "cache_size": 64,
    "block_size": 16,
    "associativity": 2,
    "latency": 1,
    "replacement_policy": "LFU"
  },
  "L1D": {
    "cache_size": 64,
    "block_size": 16,
    "associativity": 2,
    "latency": 1,
    "replacement_policy": "LFU"
  },
  "L2": {
    "cache_size": 128,
    "block_size": 16,
    "associativity": 4,
    "latency": 10,
    "replacement_policy": "LRU"
  }
}
```

- `replacement_policy` can be `"LRU"` or `"LFU"` for any cache level
- `MEMORY_LATENCY` is the penalty (in cycles) for going all the way to main memory
- `latencies.lw/sw` are the minimum MEM-stage latencies imposed by the pipeline (effective latency = max of this and cache latency)

## Cache Design

We implemented a two-level, write-back, write-allocate cache:

```
CPU
 ├─ L1I  (instruction fetch only)
 ├─ L1D  (load/store only)
 └─ L2   (unified — backs both L1I and L1D)
      └─ Main Memory
```

On a cache miss, the block is fetched from the next level and inserted back into the current level. If the set is full, a line is evicted using either LRU or LFU depending on the configured policy. Dirty evictions are written back to the level below.

The L2 enforces **inclusion** — when a block is evicted from L2, it is also invalidated in L1I/L1D.

## Output

At the end of simulation you'll see something like:

```
Simulation complete in 3241 cycles.
Total Stalls          : 847
  - Load-Use Stalls   : 120
  - Branch/Data Stalls: 210
  - Execution Stalls  : 312
  - Branch Flushes    : 205
IPC                   : 0.423
CPI                   : 2.364

--- Cache Statistics ---
L1I Miss Rate: 12.50%
L1D Miss Rate: 8.33%
L2 Miss Rate: 4.17%
```

## Writing Assembly

Your `.asm` file should have a `.data:` section and a `.text:` section:

```asm
.data:
n: .word 10

.text:
la  x5, n
lw  x6, 0(x5)    # x6 = 10
addi x7, x6, 5   # x7 = 15
```

**Tips:**
- Labels must have no spaces (e.g., `outer_loop:`, not `outer loop:`)
- Comments start with `#`

## Sample Program

The included `program.asm` runs **bubble sort** on an array and sorts it in-place in memory.

## Design Decisions

**Phase 1:**
- **Branch resolved in Decode** — We resolve branches one stage early (in ID instead of EX) so the branch penalty is only 1 cycle.
- **Forwarding paths** — We forward from EX/MEM → EX and from EX/MEM → ID (for branches), covering the most common hazard patterns.
- **`x0` is hardwired to 0** — Reads always return 0, writes are silently ignored, just like real RISC-V.

**Phase 2:**
- **LFU for L1, LRU for L2** — L1 caches are small and hot, so LFU helps retain frequently used blocks. L2 is larger and benefits from LRU's simpler recency tracking.
- **LFU tie-breaking uses LRU order** — When multiple lines have the same access count, we evict the least recently used among them. This makes LFU more stable.
- **Store buffer** — Rather than stalling the pipeline on every store, we buffer writes and drain them in the background. This lets the pipeline see a 1-cycle store latency most of the time.
- **Inclusion policy** — Enforcing inclusion (L1 ⊆ L2) simplifies coherence — if we evict from L2, we know L1 doesn't have a stale copy.
- **Multi-cycle IF stall** — When the instruction cache misses, the fetch stage buffers the fetched instruction and injects NOP bubbles into the pipeline until the miss resolves. This is handled without touching the rest of the pipeline.

## Minutes of Meeting

> All meetings: **Nikhil & Sai Rohith**

---

### 12 May 2026

**Accomplished:** Integrated the Virtual Memory (VM) subsystem directly into the 5-stage pipeline. `AddressTranslator` is now hooked up in the MEM stage. Added support for `mul` instructions with multi-cycle execution latencies. Implemented trace file (`test_trace.trc`) parsing for extensive VM evaluation.

**Design Decisions:**
- VA-to-PA translation happens inline during the MEM stage.
- TLB hits take 1 cycle; TLB misses stall the pipeline for the duration of the page walk.
- Added `config_vm.ini` to manage VM parameters independently of the cache pipeline configuration.

---


### 10 April 2026

**Accomplished:** Sai Rohith Integrated `cache_hierarchy.py` into simulator.And modified fetch , memory stages. Both LRU and LFU replacement policies verified. Store buffer drain logic tested with bubble sort program.

---

### 3 April 2026

**Accomplished:** Nikhil completed `cache.py` , `cache_hierarchy.py` with L1I, L1D, L2 .

**Design Decisions:**
- Write-back policy chosen over write-through to reduce memory traffic
- Store buffer added to `mem.py` to decouple store latency from pipeline stalls

**Next meeting:** 10 April 2026

---

### 28 March 2026

**Accomplished:** Planned Phase 2 architecture. Divided work — Nikhil takes `cache.py`,`cache_hierarchy.py` and implements only LRU, Sai Rohith implements LFU and integration into pipeline stages.

*Design Decisions:**
- LFU chosen as the second replacement policy 
-choosen non-inclusive , non-exclusive cache design , where it will fetch from main memory and keep it in L1,L2 cache , while evicted from L1 check in L2 , if it is not there keep it in L2.

**Next meeting:** 3 April 2026

---

### 7 March 2026

**Accomplished:** Nikhil implemented the hazard detection unit; Sai Rohith integrated forwarding logic and config loading from `config.json`.

**Design Decisions:**
- `beq`/`bne` comparison resolved in the **Decode (ID) stage** — hazard unit handles stall/forwarding detection for branches at this stage, consistent with real-world pipeline design.
- With forwarding enabled, branch hazards are handled via EX/MEM → ID and MEM/WB → ID forwarding paths.
- Noted that non-forwarding (stall-only) mode does not yet have dedicated branch stall logic — flagged for future work.

---

### 5 March 2026

**Accomplished:** Debugging resolved the integration issues from the previous meeting; without-forwarding mode verified to work correctly.

**Design Decisions:** Simulator supports toggling forwarding on/off via `config.json`. Both modes verified end-to-end.

**Task Assignment:**

| Member | Task | Deadline |
|--------|------|----------|
| Nikhil | Hazard detection unit (forwarding + stall logic) | 7 Mar 2026 |
| Sai Rohith | Pipeline forwarding integration in stages | 7 Mar 2026 |

---

### 4 March 2026

**Accomplished:** Nikhil completed MEM stage (`mem.py`), WB stage (`writeback.py`). Sai Rohith completed latch definitions and IF,ID/RF,EX stages. Code merged and pushed.

**Design Decisions:** Bugs found on first combined run — simulator not producing correct output. Agreed to debug individually before next meeting.

**Next meeting:** 5 March 2026

---

### 2 March 2026

**Accomplished:** Nikhil completed `parser.py` and `Memory` class. Sai Rohith set up the repo. Code shared to GitHub.

**Design Decisions:** Parser found to have bugs in instruction and label parsing — to be fixed before integration.

**Next meeting:** 4 March 2026

---

### 25 February 2026

**Design Decisions:** Finalized instruction set for **Phase 1**:
`add`, `addi`, `sub`, `la`, `lw`, `sw`, `jal`, `bne`, `beq`
(covers R / I / S / B / J types — sufficient for programs like bubble sort)

---

### 18 February 2026

**Design Decisions:**
- Sai Rohith finalized the project folder structure (`core/`, `stages/`, `components/`, `utils/`)
- Decided on a 5-stage pipeline design (IF → ID → EX → MEM → WB) with explicit latch objects between stages

**Task Assignment:**

| Member | Task | Deadline |
|--------|------|----------|
| Sai Rohith | Latches, IF stage, ID/RF stage, Execute stage | 2 Mar 2026 |
| Nikhil | MEM stage, WB stage, `Memory` class, `Instruction` class, Parser | 2 Mar 2026 |


