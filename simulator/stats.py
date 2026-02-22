"""
stats.py
────────
Collects simulation statistics and prints a summary at end of run.

Phase-1: stall_count is always 0 (single-cycle, no hazards).
Phase-2+: call record_stall() whenever a pipeline bubble is inserted.
"""


class Stats:
    def __init__(self) -> None:
        self.total_cycles: int = 0
        self.instr_count: int = 0
        self.stall_count: int = 0

    # ── Recording ─────────────────────────────────────────────────

    def record_cycle(self, instruction_completed: bool) -> None:
        """Called once per tick(). instruction_completed=True when a valid
        instruction was processed (False for warm-up NOPs or pipeline bubbles)."""
        self.total_cycles += 1
        if instruction_completed:
            self.instr_count += 1

    def record_stall(self) -> None:
        """Call when a stall cycle is inserted (Phase-2+)."""
        self.stall_count += 1
        self.total_cycles += 1

    # ── Query ─────────────────────────────────────────────────────

    @property
    def ipc(self) -> float:
        """Instructions Per Cycle."""
        return self.instr_count / self.total_cycles if self.total_cycles > 0 else 0.0

    # ── Output ────────────────────────────────────────────────────

    def report(self) -> None:
        divider = "-" * 42
        print(divider)
        print("  Simulation Statistics")
        print(divider)
        print(f"  Total cycles      : {self.total_cycles}")
        print(f"  Instructions exec : {self.instr_count}")
        print(f"  Stall cycles      : {self.stall_count}")
        print(f"  IPC               : {self.ipc:.4f}")
        print(divider)
