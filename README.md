# RISC-V Simulator — CS209P Phase 1

A Python-based RISC-V processor simulator implementing a **single-cycle execution model** with a pipeline-ready architecture, built for CS209P at IIT Tirupati.

---

## Features

- **Single-Cycle Processor (Phase 1):** All pipeline stages (IF → ID → EX → MEM → WB) complete in **one clock cycle**. IPC = 1.0.
- **Instructions supported:** `ADD`, `SUB`, `MUL` (custom), `ADDI`, `SLTI`, `LW`, `SW`, `BNE`, `JAL`
- **Two-pass assembler** with label resolution and comment stripping
- **Configuration via `config.yaml`:** memory size, instruction latencies, forwarding flag — nothing hardcoded
- **Statistics output:** total cycles, instruction count, stall count, IPC
- **Pipeline-ready design:** stage modules, latch dataclasses, and instruction-centric behaviour are all in place for Phase-2+ upgrades

---

## Requirements

```bash
pip install pyyaml pytest
```

---

## Usage

```bash
python main.py programs/bubble_sort.asm
python main.py programs/bubble_sort.asm --config config.yaml
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Project Structure

```
COA/
├── config.yaml               # Simulator configuration (latencies, memory size, etc.)
├── main.py                   # CLI entry point
├── programs/
│   └── bubble_sort.asm       # Test program — sorts [5, 3, 4, 1, 2]
├── simulator/
│   ├── config.py             # Config loader
│   ├── stats.py              # Cycle / IPC statistics
│   ├── processor.py          # SingleCycleProcessor — tick() loop
│   ├── core/
│   │   ├── register_file.py  # 32 registers (x0 always 0)
│   │   ├── memory.py         # ≥ 4 KB byte-addressable data memory
│   │   ├── alu.py            # ALU operations
│   │   ├── program_counter.py# PC with increment() and jump()
│   │   └── pipeline_regs.py  # IF_ID, ID_EX, EX_MEM, MEM_WB dataclasses
│   ├── stages/
│   │   ├── fetch.py          # IF stage
│   │   ├── decode.py         # ID/RF stage
│   │   ├── execute.py        # EX stage (PC update for branches/jumps here)
│   │   ├── mem_access.py     # MEM stage
│   │   └── writeback.py      # WB stage
│   └── assembler/
│       ├── instruction.py    # Instruction ABC + all concrete classes
│       └── parser.py         # Two-pass assembler
└── tests/
    ├── test_alu.py
    ├── test_register_file.py
    ├── test_assembler.py
    └── test_integration.py
```

---

## Architecture Notes

The codebase is structured to upgrade easily through phases:

| Phase | What changes |
|-------|-------------|
| **Phase-1** | Single-cycle; all stages execute per tick for one instruction |
| **Phase-2a** | Make latches persistent; add `remaining_cycles` counter in EX stage for variable latencies |
| **Phase-2b** | Remove some stalls with temp registers / bypass paths |
| **Phase-3** | Full pipeline — multiple instructions in different latches simultaneously; hazard detection unit |
| **Phase-3+** | Data forwarding — wire EX/MEM/WB results back to EX input mux; controlled by `config.yaml` |

---

## Meeting Minutes

---

### Date: 21-Feb-2026

**Members:** [Team Members — to be filled]

**Decisions:**
- Chose **Python** as implementation language for rapid prototyping and readability.
- Agreed on **single-cycle processor** for Phase-1 to establish the structural foundation before adding pipelining.
- Adopted **instruction-centric design**: each instruction object owns its `execute()`, `memory_access()`, and `writeback()` behaviour. Stage functions call these methods — no `if opcode ==` scattered across pipeline code.
- **Custom instruction chosen:** `MUL` (integer multiply). Latency = 3 cycles (configured in `config.yaml`), demonstrating variable-latency support from Phase-2 onward.
- **Supplementary immediate instructions added:** `ADDI` and `SLTI` — required for loop control and comparison in bubble sort; explicitly encouraged by the project spec.
- **Pipeline register dataclasses** (`IF_ID`, `ID_EX`, `EX_MEM`, `MEM_WB`) defined as structural placeholders. In Phase-1 they are local variables within `tick()`; in Phase-2+ they become persistent state.
- **PC update rule:** BNE and JAL update the PC inside their `execute()` method only — no PC logic in fetch or decode stages.
- Agreed on `config.yaml` as the configuration format (PyYAML).
- Test program: **bubble sort** on array `[5, 3, 4, 1, 2]` stored at base address 256; expected sorted output `[1, 2, 3, 4, 5]`.
