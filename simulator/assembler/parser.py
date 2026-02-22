"""
parser.py
─────────
Two-pass RISC-V assembler.

Pass 1 — Label scan:
    Iterates over non-blank, non-comment lines. When a label is found
    (text ending with ':'), its byte address (instruction_index × 4) is
    stored in label_map.

Pass 2 — Instruction build:
    Parses each clean instruction line and instantiates the matching
    Instruction object. Label names in BNE/JAL are resolved to byte
    addresses using label_map.

Supported syntax:
    add   rd, rs1, rs2
    sub   rd, rs1, rs2
    mul   rd, rs1, rs2
    addi  rd, rs1, imm
    slti  rd, rs1, imm
    lw    rd, offset(rs1)
    sw    rs2, offset(rs1)
    bne   rs1, rs2, LABEL
    jal   rd, LABEL
    LABEL:                     (label on its own line or prefixed to any instr)
    # comment                  (stripped everywhere)
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from simulator.assembler.instruction import (
    Instruction,
    ADD, SUB, MUL,
    ADDI, SLTI,
    LW, SW,
    BNE, JAL,
)


# ══════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════

def assemble(source: str) -> List[Instruction]:
    """Assemble *source* (multi-line RISC-V assembly string).

    Returns an ordered list of Instruction objects.
    Raises ValueError for unknown mnemonics or unresolved labels.
    """
    lines = source.splitlines()

    # ── Pass 1 ────────────────────────────────────────────────────
    label_map: Dict[str, int] = {}
    clean_lines: List[str] = []
    instr_index = 0

    for raw in lines:
        line = _strip_comment(raw).strip()
        if not line:
            continue

        # A line may start with  LABEL:  (possibly followed by an instruction)
        if ":" in line:
            label_part, _, rest = line.partition(":")
            label = label_part.strip()
            if label:   # valid label name found
                label_map[label] = instr_index * 4
            line = rest.strip()
            if not line:
                continue   # label-only line — no instruction to count

        clean_lines.append(line)
        instr_index += 1

    # ── Pass 2 ────────────────────────────────────────────────────
    instructions: List[Instruction] = []

    for lineno, line in enumerate(clean_lines, start=1):
        try:
            instr = _parse_line(line, label_map)
        except (KeyError, ValueError, IndexError) as exc:
            raise ValueError(
                f"Assembler error on line {lineno}: '{line}'\n  → {exc}"
            ) from exc
        instructions.append(instr)

    return instructions


# ══════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════

def _strip_comment(line: str) -> str:
    return line.split("#")[0]


def _operands(operand_str: str) -> List[str]:
    return [o.strip() for o in operand_str.split(",")]


def _reg(s: str) -> int:
    """Parse 'xN' → N.  Raises ValueError on bad format."""
    s = s.strip().lower()
    if not s.startswith("x"):
        raise ValueError(f"Expected register (e.g. x0), got '{s}'")
    n = int(s[1:])
    if not (0 <= n <= 31):
        raise ValueError(f"Register index out of range: {n}")
    return n


def _imm(s: str) -> int:
    """Parse a decimal or hex integer literal."""
    return int(s.strip(), 0)


def _mem_operand(s: str) -> Tuple[int, int]:
    """Parse 'offset(xN)' → (offset, reg_index)."""
    m = re.fullmatch(r"\s*(-?\d+)\s*\(\s*x(\d+)\s*\)\s*", s)
    if not m:
        raise ValueError(f"Invalid memory operand: '{s}'")
    return int(m.group(1)), int(m.group(2))


def _parse_line(line: str, label_map: Dict[str, int]) -> Instruction:
    """Parse a single cleaned instruction line into an Instruction object."""
    parts = line.split(None, 1)                  # mnemonic  rest
    mnemonic = parts[0].lower()
    operand_str = parts[1] if len(parts) > 1 else ""
    ops = _operands(operand_str)

    if mnemonic == "add":
        return ADD(_reg(ops[0]), _reg(ops[1]), _reg(ops[2]))

    if mnemonic == "sub":
        return SUB(_reg(ops[0]), _reg(ops[1]), _reg(ops[2]))

    if mnemonic == "mul":
        return MUL(_reg(ops[0]), _reg(ops[1]), _reg(ops[2]))

    if mnemonic == "addi":
        return ADDI(_reg(ops[0]), _reg(ops[1]), _imm(ops[2]))

    if mnemonic == "slti":
        return SLTI(_reg(ops[0]), _reg(ops[1]), _imm(ops[2]))

    if mnemonic == "lw":
        rd = _reg(ops[0])
        offset, rs1 = _mem_operand(ops[1])
        return LW(rd, rs1, offset)

    if mnemonic == "sw":
        rs2 = _reg(ops[0])
        offset, rs1 = _mem_operand(ops[1])
        return SW(rs2, rs1, offset)

    if mnemonic == "bne":
        rs1 = _reg(ops[0])
        rs2 = _reg(ops[1])
        label = ops[2].strip()
        if label not in label_map:
            raise ValueError(f"Undefined label: '{label}'")
        return BNE(rs1, rs2, label_map[label])

    if mnemonic == "jal":
        rd = _reg(ops[0])
        label = ops[1].strip()
        if label not in label_map:
            raise ValueError(f"Undefined label: '{label}'")
        return JAL(rd, label_map[label])

    raise ValueError(f"Unknown instruction mnemonic: '{mnemonic}'")
