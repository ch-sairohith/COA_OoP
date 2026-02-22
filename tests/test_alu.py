"""tests/test_alu.py — Unit tests for the ALU."""

import pytest
from simulator.core.alu import ALU


@pytest.fixture
def alu() -> ALU:
    latencies = {"ADD": 1, "SUB": 1, "MUL": 3, "SLTI": 1, "BNE": 1}
    return ALU(latencies)


def test_add_positive(alu):
    assert alu.apply("ADD", 5, 3) == 8


def test_add_zero(alu):
    assert alu.apply("ADD", 0, 0) == 0


def test_sub_positive(alu):
    assert alu.apply("SUB", 10, 4) == 6


def test_sub_negative_result(alu):
    assert alu.apply("SUB", 3, 5) == -2


def test_mul(alu):
    assert alu.apply("MUL", 4, 7) == 28


def test_mul_zero(alu):
    assert alu.apply("MUL", 100, 0) == 0


def test_slti_true(alu):
    # rs1 < imm → 1
    assert alu.apply("SLTI", 3, 5) == 1


def test_slti_false(alu):
    # rs1 >= imm → 0
    assert alu.apply("SLTI", 7, 5) == 0


def test_slti_equal(alu):
    # rs1 == imm → 0  (strictly less than)
    assert alu.apply("SLTI", 5, 5) == 0


def test_slti_negative_operand(alu):
    # -2 < 1 → 1
    assert alu.apply("SLTI", -2, 1) == 1


def test_cmp_neq_equal(alu):
    assert alu.apply("CMP_NEQ", 5, 5) == 0


def test_cmp_neq_different(alu):
    assert alu.apply("CMP_NEQ", 5, 3) == 1


def test_32bit_overflow_wraps(alu):
    # 0x7FFFFFFF + 1 wraps to -2147483648 in signed 32-bit
    assert alu.apply("ADD", 0x7FFF_FFFF, 1) == -2_147_483_648


def test_unknown_op_raises(alu):
    with pytest.raises(ValueError, match="Unknown ALU operation"):
        alu.apply("XOR", 1, 2)


def test_latency_for(alu):
    assert alu.latency_for("MUL") == 3
    assert alu.latency_for("ADD") == 1
    assert alu.latency_for("UNKNOWN") == 1   # default
