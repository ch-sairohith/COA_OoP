"""
main.py  —  RISC-V Single-Cycle Simulator entry point

Usage:
    python main.py programs/bubble_sort.asm
    python main.py programs/bubble_sort.asm --config config.yaml
"""

import argparse
import sys
from pathlib import Path

from simulator.config import load_config
from simulator.stats import Stats
from simulator.assembler.parser import assemble
from simulator.processor import SingleCycleProcessor


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RISC-V Single-Cycle Simulator (CS209P Phase-1)"
    )
    parser.add_argument("program", help="Path to .asm assembly file")
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config file (default: config.yaml)"
    )
    args = parser.parse_args()

    # ── Load configuration ────────────────────────────────────────
    cfg = load_config(args.config)

    # ── Assemble source file ──────────────────────────────────────
    asm_path = Path(args.program)
    if not asm_path.exists():
        print(f"[ERROR] File not found: {asm_path}", file=sys.stderr)
        sys.exit(1)

    source = asm_path.read_text()
    try:
        instructions = assemble(source)
    except Exception as exc:
        print(f"[ASSEMBLER ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    # ── Banner ────────────────────────────────────────────────────
    print()
    print("=" * 52)
    print("  RISC-V Single-Cycle Simulator  |  CS209P Phase-1")
    print("=" * 52)
    print(f"  Program  : {asm_path.name}")
    print(f"  Config   : {args.config}")
    print(f"  Memory   : {cfg.memory_size} bytes")
    print(f"  Forwarding: {'enabled' if cfg.forwarding else 'disabled'}")
    print(f"  Instructions assembled: {len(instructions)}")
    print("=" * 52)
    print()

    # ── Run ───────────────────────────────────────────────────────
    stats = Stats()
    proc = SingleCycleProcessor(instructions, cfg, stats)
    proc.run()

    # ── Output ────────────────────────────────────────────────────
    stats.report()

    if cfg.dump_registers:
        print("\nRegister File (non-zero only):")
        reg_dump = proc.reg_file.dump()
        any_nonzero = False
        for name, val in reg_dump.items():
            if val != 0:
                print(f"  {name:4s} = {val:10d}  (0x{val & 0xFFFFFFFF:08X})")
                any_nonzero = True
        if not any_nonzero:
            print("  (all zero)")

    if cfg.dump_memory_bytes > 0:
        print(f"\nData Memory (first {cfg.dump_memory_bytes} bytes):")
        proc.memory.dump(cfg.dump_memory_bytes)

    print()


if __name__ == "__main__":
    main()
