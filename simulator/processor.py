"""
processor.py
────────────
SingleCycleProcessor — orchestrates the 5-stage pipeline for Phase-1.

Phase-1 (single-cycle) behaviour:
  Each tick() processes EXACTLY ONE instruction through all five stages
  in sequence (IF → ID → EX → MEM → WB).  The pipeline latch dataclasses
  (if_id, id_ex, ex_mem, mem_wb) are updated every tick and stored as
  instance variables for observability and debugging.

  IPC = 1.0 — one instruction completes per clock cycle.
  Stall count = 0 — no hazards in single-cycle mode.

Phase-2 upgrade path (add at top of tick()):
  ┌──────────────────────────────────────────────────────────┐
  │ 1. Compute each stage's NEW latch using the CURRENT      │
  │    (old) latch values:                                    │
  │      new_mem_wb = mem_stage(self.ex_mem, self.memory)    │
  │      new_ex_mem = exe_stage(self.id_ex, ...)             │
  │      new_id_ex  = dec_stage(self.if_id, ...)             │
  │      new_if_id  = fch_stage(self.pc, ...)                │
  │ 2. Atomically assign:                                     │
  │      self.mem_wb, self.ex_mem, ... = new_mem_wb, ...     │
  │ Multiple instructions then occupy different latches.      │
  │ Insert NOP bubbles and freeze latches for hazard stalls.  │
  └──────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import List

from simulator.core.register_file import RegisterFile
from simulator.core.memory import Memory
from simulator.core.alu import ALU
from simulator.core.program_counter import ProgramCounter
from simulator.core.pipeline_regs import (
    IF_ID, ID_EX, EX_MEM, MEM_WB,
    nop_if_id, nop_id_ex, nop_ex_mem, nop_mem_wb,
)
from simulator.stages.fetch import fetch_stage
from simulator.stages.decode import decode_stage
from simulator.stages.execute import execute_stage
from simulator.stages.mem_access import mem_access_stage
from simulator.stages.writeback import writeback_stage
from simulator.config import Config
from simulator.stats import Stats

if False:
    from simulator.assembler.instruction import Instruction


class SingleCycleProcessor:
    """
    Phase-1 single-cycle RISC-V processor.

    All five pipeline stages execute sequentially within one tick()
    for a single instruction, giving IPC = 1.0.
    """

    def __init__(
        self,
        instructions: List["Instruction"],
        config: Config,
        stats: Stats,
    ) -> None:
        self.instructions = instructions
        self.config = config
        self.stats = stats

        # Hardware components
        self.pc       = ProgramCounter(start=0)
        self.reg_file = RegisterFile()
        self.memory   = Memory(config.memory_size)
        self.alu      = ALU(config.instruction_latencies)

        # Pipeline latches — NOP/empty at startup
        # Phase-1: refreshed every tick; Phase-2+: persistent inter-tick state
        self.if_id:  IF_ID  = nop_if_id()
        self.id_ex:  ID_EX  = nop_id_ex()
        self.ex_mem: EX_MEM = nop_ex_mem()
        self.mem_wb: MEM_WB = nop_mem_wb()

    # ── Main execution loop ───────────────────────────────────────

    def run(self) -> None:
        """Run the processor until the program counter goes out of bounds."""
        while self.tick():
            pass

    # ── Single clock cycle ────────────────────────────────────────

    def tick(self) -> bool:
        """
        Execute one clock cycle.

        Phase-1: all five stages run for the CURRENT instruction in sequence.
        Returns True while there are instructions left; False when PC is
        out of bounds (program finished).

        ─────────────────────────────────────────────────────────────
        PHASE-2 PIPELINE UPGRADE NOTE
        To convert this to a pipelined tick():
          1. Compute new latch values using OLD latch values (reverse order
             to avoid clobbering: WB→MEM→EX→ID→IF).
          2. Insert NOP bubbles where stalls are required.
          3. Atomically update: self.if_id, self.id_ex, self.ex_mem,
             self.mem_wb = new_if_id, new_id_ex, new_ex_mem, new_mem_wb.
        ─────────────────────────────────────────────────────────────
        """

        # ── IF → ID → EX → MEM → WB (single instruction, one cycle) ──
        if_id  = fetch_stage(self.pc, self.instructions)
        id_ex  = decode_stage(if_id, self.reg_file)
        ex_mem = execute_stage(id_ex, self.alu, self.pc)   # PC updated here for BNE/JAL
        mem_wb = mem_access_stage(ex_mem, self.memory)
        writeback_stage(mem_wb, self.reg_file)

        # Store latches for observability / Phase-2+ upgrade
        self.if_id  = if_id
        self.id_ex  = id_ex
        self.ex_mem = ex_mem
        self.mem_wb = mem_wb

        # Only count valid instruction cycles.
        # The final halt tick (fetch returns invalid when PC is out of bounds)
        # is NOT a real clock cycle — skipping it keeps IPC = 1.0.
        # PHASE-2 NOTE: In pipeline mode, count every tick; bubbles are stalls.
        if if_id.valid:
            self.stats.record_cycle(instruction_completed=True)

        return if_id.valid   # False → PC out of range → halt

    # ── Debug helpers ─────────────────────────────────────────────

    def dump_state(self) -> None:   # pragma: no cover
        """Print current pipeline latch state (useful for debugging)."""
        print(f"  PC      : 0x{self.pc.value:08X}")
        print(f"  IF/ID   : {self.if_id.instruction}  (valid={self.if_id.valid})")
        print(f"  ID/EX   : {self.id_ex.instruction}  (valid={self.id_ex.valid})")
        print(f"  EX/MEM  : {self.ex_mem.instruction} (valid={self.ex_mem.valid})")
        print(f"  MEM/WB  : {self.mem_wb.instruction} (valid={self.mem_wb.valid})")
