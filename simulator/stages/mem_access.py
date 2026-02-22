"""
mem_access.py  —  Memory Access (MEM) stage
────────────────────────────────────────────
Responsibilities:
  • Delegate to the instruction's own memory_access() method.
  • For LW: reads a word from data memory using the ALU-computed address.
  • For SW: writes a word to data memory.
  • For all other instructions: passes the EX_MEM latch through unchanged.
  • Returns a MEM_WB latch for the Writeback stage.
"""

from __future__ import annotations

from simulator.core.pipeline_regs import EX_MEM, MEM_WB
from simulator.core.memory import Memory


def mem_access_stage(latch: EX_MEM, memory: Memory) -> MEM_WB:
    """
    Perform memory operations for the instruction in *latch* (EX_MEM).

    Delegates to ``instruction.memory_access(latch, memory)``.
    Returns a NOP MEM_WB when the incoming latch is invalid.
    """
    if not latch.valid or latch.instruction is None:
        return MEM_WB()  # NOP / bubble

    return latch.instruction.memory_access(latch, memory)
