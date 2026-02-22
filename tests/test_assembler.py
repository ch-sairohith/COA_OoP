"""tests/test_assembler.py — Unit tests for the two-pass assembler."""

import pytest
from simulator.assembler.parser import assemble
from simulator.assembler.instruction import (
    ADD, SUB, MUL, ADDI, SLTI, LW, SW, BNE, JAL,
)


# ── R-type ────────────────────────────────────────────────────────

def test_parse_add():
    instrs = assemble("add x1, x2, x3")
    assert isinstance(instrs[0], ADD)
    assert instrs[0].rd == 1
    assert instrs[0].rs1 == 2
    assert instrs[0].rs2 == 3


def test_parse_sub():
    instrs = assemble("sub x5, x6, x7")
    assert isinstance(instrs[0], SUB)
    assert instrs[0].rd == 5


def test_parse_mul():
    instrs = assemble("mul x1, x2, x3")
    assert isinstance(instrs[0], MUL)


# ── I-type ────────────────────────────────────────────────────────

def test_parse_addi_positive():
    instrs = assemble("addi x1, x2, 10")
    assert isinstance(instrs[0], ADDI)
    assert instrs[0].imm == 10


def test_parse_addi_negative():
    instrs = assemble("addi x5, x5, -1")
    assert isinstance(instrs[0], ADDI)
    assert instrs[0].imm == -1


def test_parse_slti():
    instrs = assemble("slti x3, x4, 0")
    assert isinstance(instrs[0], SLTI)
    assert instrs[0].rd == 3
    assert instrs[0].rs1 == 4
    assert instrs[0].imm == 0


# ── Memory ────────────────────────────────────────────────────────

def test_parse_lw():
    instrs = assemble("lw x1, 8(x2)")
    assert isinstance(instrs[0], LW)
    assert instrs[0].rd == 1
    assert instrs[0].rs1 == 2
    assert instrs[0].imm == 8


def test_parse_sw():
    instrs = assemble("sw x3, 12(x4)")
    assert isinstance(instrs[0], SW)
    assert instrs[0].rs2 == 3
    assert instrs[0].rs1 == 4
    assert instrs[0].imm == 12


def test_parse_lw_zero_offset():
    instrs = assemble("lw x1, 0(x5)")
    assert instrs[0].imm == 0


# ── Branch / Jump ─────────────────────────────────────────────────

def test_bne_label_resolution():
    src = """\
LOOP: addi x1, x1, -1
      bne  x1, x0, LOOP
"""
    instrs = assemble(src)
    assert isinstance(instrs[1], BNE)
    assert instrs[1].target_pc == 0   # LOOP is at byte address 0


def test_jal_label_resolution():
    src = """\
    jal  x0, END
    add  x1, x0, x0
END:
    sub  x2, x0, x0
"""
    instrs = assemble(src)
    assert isinstance(instrs[0], JAL)
    # END is instruction index 2 → byte address 8
    assert instrs[0].target_pc == 8


def test_jal_done_label_at_end():
    src = """\
    addi x1, x0, 1
    jal  x0, DONE
DONE:
"""
    instrs = assemble(src)
    assert instrs[1].target_pc == 8   # 2 instructions → DONE at byte 8


# ── Comment and whitespace handling ──────────────────────────────

def test_comment_stripping():
    instrs = assemble("add x1, x2, x3  # a comment")
    assert isinstance(instrs[0], ADD)


def test_blank_lines_ignored():
    src = """
        add x1, x2, x3

        sub x4, x5, x6
    """
    assert len(assemble(src)) == 2


def test_inline_label_with_instruction():
    src = "START: add x1, x2, x3"
    instrs = assemble(src)
    assert len(instrs) == 1
    assert isinstance(instrs[0], ADD)


# ── Error cases ───────────────────────────────────────────────────

def test_unknown_mnemonic_raises():
    with pytest.raises(ValueError, match="Unknown instruction"):
        assemble("xor x1, x2, x3")


def test_undefined_label_raises():
    with pytest.raises(ValueError, match="Undefined label"):
        assemble("jal x0, NOWHERE")
