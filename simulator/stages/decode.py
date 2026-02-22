"""
decode.py  —  Instruction Decode / Register Fetch (ID/RF) stage
────────────────────────────────────────────────────────────────
Responsibilities:
  • Read the IF_ID latch.
  • Determine which registers the instruction needs (rs1, rs2).
  • Read operand values from the register file.
  • Pack everything into an ID_EX latch for the Execute stage.

The stage does NOT interpret opcodes — it queries the instruction
object's fields (rs1, rs2, rd, imm) which every concrete instruction
exposes through its base class interface.

Phase-2 upgrade note:
  Add hazard detection here.  Before reading registers, check if any
  register the instruction reads is marked `busy` (written by an
  in-flight instruction in EX or MEM).  If so, insert a NOP bubble
  and stall (freeze IF_ID + PC) until the hazard resolves.
  With forwarding (Phase-3): bypass the register file for RAW hazards.
"""

from __future__ import annotations

from simulator.core.pipeline_regs import IF_ID, ID_EX
from simulator.core.register_file import RegisterFile


def decode_stage(latch: IF_ID, reg_file: RegisterFile) -> ID_EX:
    """
    Decode *latch* (IF_ID) and fetch register operands.

    Returns a NOP ID_EX when the incoming latch is invalid.
    """
    if not latch.valid or latch.instruction is None:
        return ID_EX()  # NOP / bubble

    instr = latch.instruction

    # Read rs1 and rs2 from the register file.
    # An index of -1 means the instruction does not use that register;
    # we supply 0 as a safe default.
    rs1_val = reg_file.read(instr.rs1) if instr.rs1 >= 0 else 0
    rs2_val = reg_file.read(instr.rs2) if instr.rs2 >= 0 else 0

    return ID_EX(
        pc=latch.pc,
        instruction=instr,
        rd=instr.rd if instr.rd >= 0 else 0,
        rs1_val=rs1_val,
        rs2_val=rs2_val,
        imm=instr.imm,
        valid=True,
    )
