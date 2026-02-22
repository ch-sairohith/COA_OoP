"""
writeback.py  —  Writeback (WB) stage
──────────────────────────────────────
Responsibilities:
  • Delegate to the instruction's own writeback() method.
  • For instructions with reg_write=True: writes the result to the
    register file.
  • For SW, BNE, JAL-to-x0: no register update.

Phase-2 upgrade note (forwarding):
  The WB stage is the last point at which a result is "committed".
  The forwarding unit intercepts the value here (and from EX/MEM) to
  supply it directly to the ID/EX latch inputs — bypassing the register
  file read for RAW hazards.
"""

from __future__ import annotations

from simulator.core.pipeline_regs import MEM_WB
from simulator.core.register_file import RegisterFile


def writeback_stage(latch: MEM_WB, reg_file: RegisterFile) -> None:
    """
    Write back the result in *latch* (MEM_WB) to the register file.

    Delegates to ``instruction.writeback(latch, reg_file)``.
    Does nothing when the incoming latch is invalid (NOP / bubble).
    """
    if not latch.valid or latch.instruction is None:
        return  # NOP / bubble — nothing to write

    latch.instruction.writeback(latch, reg_file)
