"""
alu.py
──────
Arithmetic Logic Unit.

Supports the operations required by all Phase-1 instructions.
The ALU knows nothing about instructions or the pipeline — it just
maps an operation name to a numeric result.

Phase-2 upgrade hint:
    The `latencies` dict is already stored here.  In the Execute stage,
    after calling apply(), check latency_for(op) and insert stall cycles
    if latency > 1.
"""

from __future__ import annotations
from typing import Dict


class ALU:
    """Performs arithmetic and comparison operations."""

    # ── Supported operations ──────────────────────────────────────
    _OPS: Dict[str, object] = {
        "ADD":     lambda a, b: a + b,
        "SUB":     lambda a, b: a - b,
        "MUL":     lambda a, b: a * b,
        "SLTI":    lambda a, b: 1 if a < b else 0,   # set if less than (signed)
        "CMP_NEQ": lambda a, b: 0 if a == b else 1,  # used by BNE
        "PASS_A":  lambda a, b: a,                    # pass a through (unused in Ph1)
    }

    def __init__(self, latencies: Dict[str, int] | None = None) -> None:
        # latencies keyed by instruction opcode (ADD, MUL …), not ALU op.
        # Stored for Phase-2 use — the Execute stage reads them.
        self.latencies: Dict[str, int] = latencies or {}

    def apply(self, op: str, a: int, b: int) -> int:
        """Evaluate ALU operation *op* on operands *a* and *b*.

        Result is masked to a signed 32-bit integer.
        Raises ValueError for unknown operations.
        """
        fn = self._OPS.get(op)
        if fn is None:
            raise ValueError(f"Unknown ALU operation: '{op}'")
        result = fn(a, b)
        return _to_int32(result)

    def latency_for(self, instr_opcode: str) -> int:
        """Return configured latency for instruction opcode (default 1)."""
        return self.latencies.get(instr_opcode.upper(), 1)


# ── Helper ────────────────────────────────────────────────────────

def _to_int32(val: int) -> int:
    """Clamp *val* to the signed 32-bit range."""
    val = val & 0xFFFF_FFFF
    if val >= 0x8000_0000:
        val -= 0x1_0000_0000
    return val
