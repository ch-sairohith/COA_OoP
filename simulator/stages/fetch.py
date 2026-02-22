"""
fetch.py  —  Instruction Fetch (IF) stage
──────────────────────────────────────────
Responsibilities:
  • Read the instruction at the current PC from the instruction list.
  • Advance PC by 4 (sequential increment).
  • Return an IF_ID latch for the Decode stage.

PC update rule:
  BNE (taken) and JAL override PC inside THEIR OWN execute() methods.
  The Fetch stage only ever does PC += 4 — never a branch/jump.

Phase-2 upgrade note:
  In a pipelined processor, Fetch produces a new IF_ID latch every tick.
  When a stall is inserted, Fetch is paused (PC not incremented; old IF_ID
  latch frozen) until the hazard clears.
"""

from __future__ import annotations
from typing import List

from simulator.core.pipeline_regs import IF_ID
from simulator.core.program_counter import ProgramCounter

if False:  # TYPE_CHECKING
    from simulator.assembler.instruction import Instruction


def fetch_stage(
    pc: ProgramCounter,
    instructions: List["Instruction"],
) -> IF_ID:
    """
    Fetch the instruction at *pc.value* and advance PC by 4.

    Returns IF_ID(valid=False) when PC is out of bounds — signals
    to the processor that the program has finished.
    """
    idx = pc.value // 4

    if idx < 0 or idx >= len(instructions):
        # Program counter past the last instruction → halt.
        return IF_ID(pc=pc.value, instruction=None, valid=False)

    instruction = instructions[idx]
    current_pc = pc.value
    pc.increment()  # PC += 4  (may be overridden by Execute for BNE/JAL)

    return IF_ID(pc=current_pc, instruction=instruction, valid=True)
