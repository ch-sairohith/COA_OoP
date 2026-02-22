"""
tests/test_integration.py
─────────────────────────
End-to-end integration tests for the single-cycle processor.

Runs bubble_sort.asm and verifies:
  1. Sorted array is correct in data memory.
  2. IPC = 1.0  (single-cycle: one instruction per cycle).
  3. Stall count = 0  (no hazards in Phase-1).
"""

import pytest
from pathlib import Path

from simulator.assembler.parser import assemble
from simulator.config import Config
from simulator.stats import Stats
from simulator.processor import SingleCycleProcessor


# ── Helpers ───────────────────────────────────────────────────────

def _make_config() -> Config:
    return Config(
        memory_size=4096,
        forwarding=False,
        instruction_latencies={
            "ADD": 1, "SUB": 1, "MUL": 3,
            "LW": 2, "SW": 1,
            "BNE": 1, "JAL": 1,
            "ADDI": 1, "SLTI": 1,
        },
        dump_registers=False,
        dump_memory_bytes=0,
    )


def _run_bubble_sort():
    """Assemble and run bubble_sort.asm; return (processor, stats)."""
    src = (Path(__file__).parent.parent / "programs" / "bubble_sort.asm").read_text()
    instructions = assemble(src)
    stats = Stats()
    proc = SingleCycleProcessor(instructions, _make_config(), stats)
    proc.run()
    return proc, stats


# ── Tests ─────────────────────────────────────────────────────────

def test_bubble_sort_result():
    """Array [5,3,4,1,2] should be sorted to [1,2,3,4,5] in memory."""
    proc, _ = _run_bubble_sort()
    base = 256
    result = [proc.memory.load_word(base + i * 4) for i in range(5)]
    assert result == [1, 2, 3, 4, 5], f"Sort failed: got {result}"


def test_ipc_equals_one():
    """Phase-1 single-cycle processor must achieve IPC = 1.0."""
    _, stats = _run_bubble_sort()
    assert stats.ipc == pytest.approx(1.0), f"IPC should be 1.0, got {stats.ipc}"


def test_stall_count_is_zero():
    """No stalls in Phase-1."""
    _, stats = _run_bubble_sort()
    assert stats.stall_count == 0


def test_instruction_count_matches_cycles():
    """For single-cycle, total cycles == instruction count."""
    _, stats = _run_bubble_sort()
    assert stats.total_cycles == stats.instr_count


def test_simple_add():
    """Run a trivial ADD program and verify register state."""
    src = "addi x1, x0, 7\naddi x2, x0, 3\nadd  x3, x1, x2"
    instrs = assemble(src)
    stats = Stats()
    proc = SingleCycleProcessor(instrs, _make_config(), stats)
    proc.run()
    assert proc.reg_file.read(3) == 10


def test_lw_sw_roundtrip():
    """SW then LW at the same address should return the stored value."""
    src = """\
addi x1, x0, 256
addi x2, x0, 42
sw   x2, 0(x1)
lw   x3, 0(x1)
"""
    instrs = assemble(src)
    stats = Stats()
    proc = SingleCycleProcessor(instrs, _make_config(), stats)
    proc.run()
    assert proc.reg_file.read(3) == 42


def test_bne_skips_on_equal():
    """BNE should NOT branch when rs1 == rs2."""
    src = """\
addi x1, x0, 5
addi x2, x0, 5
bne  x1, x2, SKIP
addi x3, x0, 99
SKIP:
"""
    instrs = assemble(src)
    stats = Stats()
    proc = SingleCycleProcessor(instrs, _make_config(), stats)
    proc.run()
    assert proc.reg_file.read(3) == 99   # fell through; addi x3 executed


def test_bne_branches_on_not_equal():
    """BNE should branch when rs1 != rs2, skipping the next instruction."""
    src = """\
addi x1, x0, 3
addi x2, x0, 7
bne  x1, x2, END
addi x3, x0, 99
END:
"""
    instrs = assemble(src)
    stats = Stats()
    proc = SingleCycleProcessor(instrs, _make_config(), stats)
    proc.run()
    assert proc.reg_file.read(3) == 0    # addi x3 was skipped by the branch


def test_jal_stores_return_address():
    """JAL rd, label must store PC+4 in rd."""
    src = """\
jal  x1, TARGET
addi x2, x0, 0
TARGET:
"""
    instrs = assemble(src)
    stats = Stats()
    proc = SingleCycleProcessor(instrs, _make_config(), stats)
    proc.run()
    # JAL is at pc=0; return address = 4; TARGET is at pc=8
    assert proc.reg_file.read(1) == 4
