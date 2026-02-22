"""
instruction.py
──────────────
Instruction class hierarchy for the RISC-V simulator.

Design rule (instruction-centric behaviour):
  Each concrete instruction class owns the logic for all three of its
  active pipeline stages.  Stage functions (execute.py, mem_access.py,
  writeback.py) call these methods — they contain NO opcode switch logic.

Base class fields (set by every concrete class):
  rd  : int   destination register index  (-1 = not used)
  rs1 : int   source register 1 index     (-1 = not used)
  rs2 : int   source register 2 index     (-1 = not used)
  imm : int   sign-extended immediate / resolved label byte-address

Concrete classes implemented:
  R-type : ADD, SUB, MUL (custom)
  I-type : ADDI, SLTI
  Load   : LW
  Store  : SW
  Branch : BNE
  Jump   : JAL
  Special: NOP  (pipeline bubble / empty fetch)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.core.pipeline_regs import ID_EX, EX_MEM, MEM_WB
    from simulator.core.alu import ALU
    from simulator.core.program_counter import ProgramCounter
    from simulator.core.register_file import RegisterFile
    from simulator.core.memory import Memory

# Re-import at runtime for isinstance / usage inside methods
from simulator.core.pipeline_regs import (
    ID_EX, EX_MEM, MEM_WB,
    nop_ex_mem, nop_mem_wb,
)
from simulator.core.alu import ALU
from simulator.core.program_counter import ProgramCounter
from simulator.core.register_file import RegisterFile
from simulator.core.memory import Memory


# ══════════════════════════════════════════════════════════════════
# Abstract base
# ══════════════════════════════════════════════════════════════════

class Instruction(ABC):
    """Abstract base for all RISC-V instructions."""

    # Subclasses MUST set these in __init__
    rd:  int   # destination register  (-1 = unused)
    rs1: int   # source register 1     (-1 = unused)
    rs2: int   # source register 2     (-1 = unused)
    imm: int   # immediate / label target PC

    @abstractmethod
    def execute(
        self,
        latch: "ID_EX",
        alu: "ALU",
        pc: "ProgramCounter",
    ) -> "EX_MEM":
        """ALU computation and (for BNE/JAL) PC update."""

    @abstractmethod
    def memory_access(self, latch: "EX_MEM", memory: "Memory") -> "MEM_WB":
        """Data memory read (LW) or write (SW); pass-through for others."""

    @abstractmethod
    def writeback(self, latch: "MEM_WB", reg_file: "RegisterFile") -> None:
        """Write result to destination register; no-op for SW/BNE."""

    @abstractmethod
    def __str__(self) -> str: ...


# ══════════════════════════════════════════════════════════════════
# R-type base  (ADD, SUB, MUL share identical MEM + WB behaviour)
# ══════════════════════════════════════════════════════════════════

class _RType(Instruction):
    """Base for register-register instructions (ADD / SUB / MUL)."""

    ALU_OP: str = ""   # Overridden by each subclass

    def __init__(self, rd: int, rs1: int, rs2: int) -> None:
        self.rd  = rd
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = 0

    def execute(self, latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
        result = alu.apply(self.ALU_OP, latch.rs1_val, latch.rs2_val)
        return EX_MEM(
            instruction=self,
            rd=latch.rd,
            alu_result=result,
            rs2_val=latch.rs2_val,
            reg_write=True,
            valid=True,
        )

    def memory_access(self, latch: EX_MEM, memory: Memory) -> MEM_WB:
        return MEM_WB(
            instruction=self,
            rd=latch.rd,
            result=latch.alu_result,
            reg_write=True,
            valid=True,
        )

    def writeback(self, latch: MEM_WB, reg_file: RegisterFile) -> None:
        reg_file.write(latch.rd, latch.result)


class ADD(_RType):
    ALU_OP = "ADD"
    def __str__(self) -> str:
        return f"add  x{self.rd}, x{self.rs1}, x{self.rs2}"


class SUB(_RType):
    ALU_OP = "SUB"
    def __str__(self) -> str:
        return f"sub  x{self.rd}, x{self.rs1}, x{self.rs2}"


class MUL(_RType):
    """Custom instruction: integer multiply (latency = 3 in config.yaml)."""
    ALU_OP = "MUL"
    def __str__(self) -> str:
        return f"mul  x{self.rd}, x{self.rs1}, x{self.rs2}"


# ══════════════════════════════════════════════════════════════════
# I-type base  (ADDI, SLTI share identical MEM + WB behaviour)
# ══════════════════════════════════════════════════════════════════

class _IType(Instruction):
    """Base for register-immediate arithmetic instructions."""

    ALU_OP: str = ""

    def __init__(self, rd: int, rs1: int, imm: int) -> None:
        self.rd  = rd
        self.rs1 = rs1
        self.rs2 = -1   # unused
        self.imm = imm

    def execute(self, latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
        result = alu.apply(self.ALU_OP, latch.rs1_val, latch.imm)
        return EX_MEM(
            instruction=self,
            rd=latch.rd,
            alu_result=result,
            rs2_val=0,
            reg_write=True,
            valid=True,
        )

    def memory_access(self, latch: EX_MEM, memory: Memory) -> MEM_WB:
        return MEM_WB(
            instruction=self,
            rd=latch.rd,
            result=latch.alu_result,
            reg_write=True,
            valid=True,
        )

    def writeback(self, latch: MEM_WB, reg_file: RegisterFile) -> None:
        reg_file.write(latch.rd, latch.result)


class ADDI(_IType):
    ALU_OP = "ADD"
    def __str__(self) -> str:
        return f"addi x{self.rd}, x{self.rs1}, {self.imm}"


class SLTI(_IType):
    """Set rd = 1 if rs1 < imm (signed), else 0."""
    ALU_OP = "SLTI"
    def __str__(self) -> str:
        return f"slti x{self.rd}, x{self.rs1}, {self.imm}"


# ══════════════════════════════════════════════════════════════════
# LW — Load Word
# ══════════════════════════════════════════════════════════════════

class LW(Instruction):
    """lw rd, offset(rs1)  →  rd = Memory[rs1 + offset]"""

    def __init__(self, rd: int, rs1: int, offset: int) -> None:
        self.rd  = rd
        self.rs1 = rs1
        self.rs2 = -1
        self.imm = offset

    def execute(self, latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
        addr = alu.apply("ADD", latch.rs1_val, latch.imm)
        return EX_MEM(
            instruction=self,
            rd=latch.rd,
            alu_result=addr,
            mem_read=True,
            reg_write=True,
            valid=True,
        )

    def memory_access(self, latch: EX_MEM, memory: Memory) -> MEM_WB:
        value = memory.load_word(latch.alu_result)
        return MEM_WB(
            instruction=self,
            rd=latch.rd,
            result=value,
            reg_write=True,
            valid=True,
        )

    def writeback(self, latch: MEM_WB, reg_file: RegisterFile) -> None:
        reg_file.write(latch.rd, latch.result)

    def __str__(self) -> str:
        return f"lw   x{self.rd}, {self.imm}(x{self.rs1})"


# ══════════════════════════════════════════════════════════════════
# SW — Store Word
# ══════════════════════════════════════════════════════════════════

class SW(Instruction):
    """sw rs2, offset(rs1)  →  Memory[rs1 + offset] = rs2"""

    def __init__(self, rs2: int, rs1: int, offset: int) -> None:
        self.rd  = -1   # no destination register
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = offset

    def execute(self, latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
        addr = alu.apply("ADD", latch.rs1_val, latch.imm)
        return EX_MEM(
            instruction=self,
            rd=-1,
            alu_result=addr,
            rs2_val=latch.rs2_val,   # data to store
            mem_write=True,
            reg_write=False,
            valid=True,
        )

    def memory_access(self, latch: EX_MEM, memory: Memory) -> MEM_WB:
        memory.store_word(latch.alu_result, latch.rs2_val)
        return MEM_WB(
            instruction=self,
            rd=-1,
            result=0,
            reg_write=False,
            valid=True,
        )

    def writeback(self, latch: MEM_WB, reg_file: RegisterFile) -> None:
        pass   # SW never writes to a register

    def __str__(self) -> str:
        return f"sw   x{self.rs2}, {self.imm}(x{self.rs1})"


# ══════════════════════════════════════════════════════════════════
# BNE — Branch if Not Equal
# ══════════════════════════════════════════════════════════════════

class BNE(Instruction):
    """bne rs1, rs2, label  →  if rs1 != rs2: PC = target_pc"""

    def __init__(self, rs1: int, rs2: int, target_pc: int) -> None:
        self.rd  = -1
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = target_pc      # resolved byte address of the label
        self.target_pc = target_pc

    def execute(self, latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
        not_equal = alu.apply("CMP_NEQ", latch.rs1_val, latch.rs2_val)
        if not_equal:
            pc.jump(self.target_pc)
        return EX_MEM(
            instruction=self,
            rd=-1,
            alu_result=not_equal,
            reg_write=False,
            valid=True,
        )

    def memory_access(self, latch: EX_MEM, memory: Memory) -> MEM_WB:
        return MEM_WB(instruction=self, rd=-1, result=0,
                      reg_write=False, valid=True)

    def writeback(self, latch: MEM_WB, reg_file: RegisterFile) -> None:
        pass   # BNE never writes to a register

    def __str__(self) -> str:
        return f"bne  x{self.rs1}, x{self.rs2}, 0x{self.target_pc:X}"


# ══════════════════════════════════════════════════════════════════
# JAL — Jump and Link
# ══════════════════════════════════════════════════════════════════

class JAL(Instruction):
    """jal rd, label  →  rd = PC+4;  PC = target_pc"""

    def __init__(self, rd: int, target_pc: int) -> None:
        self.rd  = rd
        self.rs1 = -1
        self.rs2 = -1
        self.imm = target_pc
        self.target_pc = target_pc

    def execute(self, latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
        return_addr = latch.pc + 4   # address of the instruction after JAL
        pc.jump(self.target_pc)      # unconditional jump
        return EX_MEM(
            instruction=self,
            rd=latch.rd,
            alu_result=return_addr,
            reg_write=(latch.rd != 0),   # jal x0, LABEL → discard return addr
            valid=True,
        )

    def memory_access(self, latch: EX_MEM, memory: Memory) -> MEM_WB:
        return MEM_WB(
            instruction=self,
            rd=latch.rd,
            result=latch.alu_result,
            reg_write=latch.reg_write,
            valid=True,
        )

    def writeback(self, latch: MEM_WB, reg_file: RegisterFile) -> None:
        if latch.reg_write:
            reg_file.write(latch.rd, latch.result)

    def __str__(self) -> str:
        return f"jal  x{self.rd}, 0x{self.target_pc:X}"


# ══════════════════════════════════════════════════════════════════
# NOP — pipeline bubble / empty fetch
# ══════════════════════════════════════════════════════════════════

class NOP(Instruction):
    """No-operation; used as a pipeline bubble in Phase-2+."""

    def __init__(self) -> None:
        self.rd  = -1
        self.rs1 = -1
        self.rs2 = -1
        self.imm = 0

    def execute(self, latch: ID_EX, alu: ALU, pc: ProgramCounter) -> EX_MEM:
        return EX_MEM()

    def memory_access(self, latch: EX_MEM, memory: Memory) -> MEM_WB:
        return MEM_WB()

    def writeback(self, latch: MEM_WB, reg_file: RegisterFile) -> None:
        pass

    def __str__(self) -> str:
        return "nop"
