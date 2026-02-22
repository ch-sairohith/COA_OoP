"""
execute.py  —  Execute (EX) stage
──────────────────────────────────
Responsibilities:
  • Delegate to the instruction's own execute() method.
  • The instruction computes the ALU result AND updates PC for BNE/JAL.
  • Returns an EX_MEM latch for the Memory stage.

PC update contract:
  BNE and JAL are the ONLY instructions that call pc.jump() — and they
  do so inside their own execute() method.  No other stage touches PC
  for branch/jump purposes.

Phase-2 upgrade note:
  After calling instr.execute(), check alu.latency_for(instr opcode).
  If latency > 1, keep this latch stalled for (latency-1) extra cycles
  by returning the SAME EX_MEM latch without marking it `done`, and
  inserting a NOP into the ID_EX latch fed to the next tick.
"""

from __future__ import annotations

from simulator.core.pipeline_regs import ID_EX, EX_MEM
from simulator.core.alu import ALU
from simulator.core.program_counter import ProgramCounter


def execute_stage(latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
    """
    Execute the instruction in *latch* (ID_EX).

    Delegates to ``instruction.execute(latch, alu, pc)``.
    BNE/JAL will call ``pc.jump()`` inside that method if needed.

    Returns a NOP EX_MEM when the incoming latch is invalid.
    """
    if not latch.valid or latch.instruction is None:
        return EX_MEM()  # NOP / bubble

    return latch.instruction.execute(latch, alu, pc)
