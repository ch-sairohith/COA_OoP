"""
memory.py
─────────
Byte-addressable data memory backed by a Python bytearray.

Word size : 4 bytes (little-endian), matching RISC-V convention.
Default   : 4 096 bytes (4 KB) — configurable via config.yaml.

Code is NOT stored in memory (instructions are read directly from the
assembled list in the processor — a design choice that simplifies Phase-1
while remaining consistent with Harvard-architecture simulator conventions).
"""

import struct


class Memory:
    """Byte-addressable data memory."""

    WORD_SIZE = 4  # bytes

    def __init__(self, size: int = 4096) -> None:
        if size < 4096:
            raise ValueError(f"Memory size must be >= 4096, got {size}")
        self._mem = bytearray(size)
        self.size = size

    # ── Word-level access (4-byte, little-endian) ─────────────────

    def load_word(self, addr: int) -> int:
        """Load a signed 32-bit word from byte address *addr*."""
        self._check_aligned(addr)
        raw = struct.unpack_from("<I", self._mem, addr)[0]  # unsigned
        # Sign-extend to Python int
        return raw if raw < 0x8000_0000 else raw - 0x1_0000_0000

    def store_word(self, addr: int, value: int) -> None:
        """Store a 32-bit word to byte address *addr* (only low 32 bits stored)."""
        self._check_aligned(addr)
        raw = value & 0xFFFF_FFFF
        struct.pack_into("<I", self._mem, addr, raw)

    # ── Utility ───────────────────────────────────────────────────

    def dump(self, n_bytes: int = 64) -> None:
        """Print a hex dump of the first *n_bytes* bytes."""
        n_bytes = min(n_bytes, self.size)
        header = "  Addr  | " + "  ".join(f"{i:02X}" for i in range(16))
        print(f"  {header}")
        print("  " + "-" * (len(header) + 2))
        for row_start in range(0, n_bytes, 16):
            row = self._mem[row_start: row_start + 16]
            hex_str = "  ".join(f"{b:02X}" for b in row)
            print(f"  {row_start:04X}   | {hex_str}")

    # ── Internal ──────────────────────────────────────────────────

    def _check_aligned(self, addr: int) -> None:
        if addr % self.WORD_SIZE != 0:
            raise MemoryError(f"Unaligned word access at address 0x{addr:X}")
        if not (0 <= addr <= self.size - self.WORD_SIZE):
            raise MemoryError(
                f"Memory address 0x{addr:X} out of range "
                f"(memory size = {self.size} bytes)"
            )
