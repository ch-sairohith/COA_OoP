# RISC-V Pipelined Processor Simulator

A Python-based simulation of a 5-stage pipelined RISC-V processor.

## What This Is

This simulator models a classic 5-stage RISC-V pipeline:

```
IF → ID → EX → MEM → WB
```

It supports data forwarding, stall detection, and early branch resolution — basically everything you'd expect from a real pipelined CPU. We also wrote an assembler/parser so you can write actual `.asm` files and run them through the simulator.

## Features

- **5-stage pipeline** — Fetch, Decode, Execute, Memory, Writeback
- **Data forwarding** — EX-to-EX , MEM-to-EX MEM-to-ID and EX-to-ID forwarding to minimize stalls
- **Hazard detection** — Handles load-use stalls, data hazards, and branch hazards
- **Early branch resolution** — Branches are resolved in the Decode stage to reduce branch penalty
- **Configurable** — Forwarding can be turned on/off via `config.json`
- **Custom assembler** — Parses a subset of RISC-V assembly directly

## Supported Instructions

| Type | Instructions |
|------|-------------|
| R-type | `add`, `sub`, `slt` |
| I-type | `addi`, `lw` |
| S-type | `sw` |
| B-type | `beq`, `bne` |
| J-type | `jal` |
| Pseudo | `la`, `j` |

## Project Structure

```
COA_OoP/
├── main.py                  # Entry point — run this
├── program.asm              # assembly program 
├── config.json              
│
├── core/
│   ├── simulator.py         # Main simulation loop
│   ├── hazard_unit.py       # Forwarding + stall logic
│   └── latches.py           # Pipeline latch dataclasses
│
├── stages/
│   ├── fetch.py             # IF stage
│   ├── decode.py            # ID stage (+ early branch resolution)
│   ├── execute.py           # EX stage
│   ├── mem.py               # MEM stage
│   └── writeback.py         # WB stage
│
├── components/
│   ├── register.py          # 32 general-purpose registers (x0–x31)
│   ├── data_mem.py          # Byte-addressable data memory (4 KB)
│   └── Instruction_mem.py   # Instruction memory
│
└── utils/
    ├── parser.py            # Assembles .asm → Instruction objects
    └── Instruction.py       # Instruction dataclass
```

## How to Run

> Make sure you have Python 3 installed.

1. Write your assembly program in `program.asm`
2. Run:
   ```bash
   python main.py
   ```
3. The simulator will print the final register state and any non-zero memory values.

## Configuration

Edit `config.json` to change simulator behaviour:

```json
{
  "forwarding_enabled": true
}
```

Set `forwarding_enabled` to `false` to run without data forwarding (the simulator will insert stalls instead).

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

The included `program.asm` runs **bubble sort** on a 20-element array and sorts it in-place in memory. It completes in ~3000 cycles with forwarding enabled.

## Design Decisions

- **Branch resolved in Decode** — We resolve branches one stage early (in ID instead of EX) so the branch penalty is only 1 cycle (just the IF stage instruction that got fetched speculatively needs to be flushed).
- **Forwarding paths** — We forward from EX/MEM → EX and from EX/MEM → ID (for branches), covering the most common hazard patterns.
- **`x0` is hardwired to 0** — Reads always return 0, writes are silently ignored, just like real RISC-V.

## Minutes of Meeting

> All meetings: **Nikhil  & Sai Rohith**

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


