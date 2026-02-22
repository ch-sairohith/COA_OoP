"""
program_counter.py
──────────────────
Models the Program Counter (PC).

Convention: PC is a byte address; instructions are 4 bytes apart.
  instruction[i] lives at byte address i * 4.

increment() is called by the Fetch stage after each instruction is read.
jump(addr)  is called by the Execute stage for BNE (taken) and JAL.

The Fetch stage calls increment() — making PC point to the *next*
sequential instruction — before Execute runs.  If Execute then calls
jump(), the sequential increment is overridden with the branch target.
On the next tick, Fetch reads the (already updated) PC.
"""


class ProgramCounter:
    """Byte-addressed program counter."""

    def __init__(self, start: int = 0) -> None:
        self.value: int = start

    def increment(self) -> None:
        """Advance PC to the next instruction (PC += 4)."""
        self.value += 4

    def jump(self, target: int) -> None:
        """Set PC to *target* (used by BNE taken-branch and JAL)."""
        self.value = target

    def instruction_index(self) -> int:
        """Return the current instruction list index (PC // 4)."""
        return self.value // 4

    def __repr__(self) -> str:
        return f"PC(0x{self.value:08X})"
