"""tests/test_register_file.py — Unit tests for the RegisterFile."""

import pytest
from simulator.core.register_file import RegisterFile


@pytest.fixture
def rf() -> RegisterFile:
    return RegisterFile()


def test_all_registers_initialise_to_zero(rf):
    for i in range(32):
        assert rf.read(i) == 0


def test_write_and_read(rf):
    rf.write(5, 42)
    assert rf.read(5) == 42


def test_x0_always_zero(rf):
    rf.write(0, 999)
    assert rf.read(0) == 0


def test_multiple_registers_independent(rf):
    rf.write(1, 10)
    rf.write(2, 20)
    rf.write(31, 100)
    assert rf.read(1) == 10
    assert rf.read(2) == 20
    assert rf.read(31) == 100


def test_overwrite_register(rf):
    rf.write(7, 50)
    rf.write(7, 99)
    assert rf.read(7) == 99


def test_value_masked_to_32bit(rf):
    # Values are sign-extended to 32-bit; check that large values wrap
    rf.write(3, 0x1_FFFF_FFFF)   # > 32 bits
    # lowest 32 bits = 0xFFFFFFFF = -1 signed
    assert rf.read(3) == -1


def test_dump_returns_all_registers(rf):
    rf.write(10, 77)
    d = rf.dump()
    assert len(d) == 32
    assert d["x10"] == 77
    assert d["x0"] == 0


def test_out_of_range_raises(rf):
    with pytest.raises(IndexError):
        rf.read(32)
    with pytest.raises(IndexError):
        rf.write(32, 0)
