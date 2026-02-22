"""
register_file.py
────────────────
Models the RISC-V register file: 32 general-purpose registers x0–x31.
x0 is hard-wired to 0; writes to x0 are silently ignored.

Phase-2 upgrade hint:
    Add a `busy[32]` boolean flag array.  Mark a register busy in ID
    when an instruction writes to it; clear the flag in WB.
    The decode stage checks busy flags to detect RAW hazards.
"""


class RegisterFile:
    """32-register RISC-V register file."""

    NUM_REGS = 32

    def __init__(self) -> None:
        self._regs: list[int] = [0] * self.NUM_REGS

    # ── Read / Write ──────────────────────────────────────────────

    def read(self, reg: int) -> int:
        """Return the value of register *reg* (x0 always returns 0)."""
        self._validate(reg)
        return self._regs[reg]  # _regs[0] is always 0 — enforced in write()

    def write(self, reg: int, value: int) -> None:
        """Write *value* to register *reg*.  Writes to x0 are ignored."""
        self._validate(reg)
        if reg == 0:
            return  # x0 is immutable
        self._regs[reg] = _to_int32(value)

    # ── Utility ───────────────────────────────────────────────────

    def dump(self) -> dict[str, int]:
        """Return a {name: value} mapping for all 32 registers."""
        return {f"x{i}": self._regs[i] for i in range(self.NUM_REGS)}

    def _validate(self, reg: int) -> None:
        if not (0 <= reg < self.NUM_REGS):
            raise IndexError(f"Register index out of range: {reg}")

    def __repr__(self) -> str:  # pragma: no cover
        lines = [f"  x{i:02d} = {self._regs[i]:10d}" for i in range(self.NUM_REGS)]
        return "RegisterFile:\n" + "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────

def _to_int32(val: int) -> int:
    """Wrap *val* into the signed 32-bit integer range."""
    val = val & 0xFFFF_FFFF
    if val >= 0x8000_0000:
        val -= 0x1_0000_0000
    return val
