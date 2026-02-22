"""
pipeline_regs.py
────────────────
Inter-stage latch dataclasses for the 5-stage RISC-V pipeline:

  Fetch → [IF_ID] → Decode → [ID_EX] → Execute → [EX_MEM] → Memory → [MEM_WB] → Writeback

Phase-1 (single-cycle):
    These dataclasses are instantiated as LOCAL variables within each tick().
    One instruction flows through all five stages in a single tick.
    `valid = False` indicates a NOP / bubble.

Phase-2+ (pipeline) upgrade path:
    1. Store latches as instance variables on Processor (self.if_id, etc.).
    2. In tick(), compute NEW latch values from the CURRENT latch values
       running each stage independently, then atomically assign all at once.
    3. Multiple instructions then occupy different latches simultaneously.
    4. Add `stall: bool` to freeze a latch when a hazard is detected.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    # Avoid circular import at runtime; only used for type hints.
    from simulator.assembler.instruction import Instruction


@dataclass
class IF_ID:
    """Latch between Fetch and Decode stages."""
    pc: int = 0                                    # byte address of fetched instruction
    instruction: Optional["Instruction"] = None   # None → NOP / bubble
    valid: bool = False                            # False → no real instruction here


@dataclass
class ID_EX:
    """Latch between Decode and Execute stages."""
    pc: int = 0
    instruction: Optional["Instruction"] = None
    rd: int = 0          # destination register index (-1 if unused)
    rs1_val: int = 0     # value read from rs1
    rs2_val: int = 0     # value read from rs2
    imm: int = 0         # sign-extended immediate or resolved label byte-address
    valid: bool = False


@dataclass
class EX_MEM:
    """Latch between Execute and Memory stages."""
    instruction: Optional["Instruction"] = None
    rd: int = 0
    alu_result: int = 0
    rs2_val: int = 0     # store data forwarded for SW instructions
    mem_read: bool = False
    mem_write: bool = False
    reg_write: bool = False
    valid: bool = False


@dataclass
class MEM_WB:
    """Latch between Memory and Writeback stages."""
    instruction: Optional["Instruction"] = None
    rd: int = 0
    result: int = 0      # final value to write into the register file
    reg_write: bool = False
    valid: bool = False


# ── NOP factories ─────────────────────────────────────────────────
# Convenience helpers for the Processor to initialise empty latches.

def nop_if_id()  -> IF_ID:  return IF_ID()
def nop_id_ex()  -> ID_EX:  return ID_EX()
def nop_ex_mem() -> EX_MEM: return EX_MEM()
def nop_mem_wb() -> MEM_WB: return MEM_WB()
