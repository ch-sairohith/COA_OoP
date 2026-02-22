"""
config.py
─────────
Reads config.yaml and exposes a Config dataclass.
All simulator parameters come from here — nothing is hardcoded.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict


@dataclass
class Config:
    """Parsed simulator configuration."""
    memory_size: int
    forwarding: bool
    instruction_latencies: Dict[str, int]
    dump_registers: bool
    dump_memory_bytes: int

    def latency_for(self, opcode: str) -> int:
        """Return the configured latency for an instruction (default 1)."""
        return self.instruction_latencies.get(opcode.upper(), 1)


def load_config(path: str = "config.yaml") -> Config:
    """Load and parse the YAML configuration file."""
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = yaml.safe_load(cfg_path.read_text())

    return Config(
        memory_size=int(data.get("memory_size", 4096)),
        forwarding=bool(data.get("forwarding", False)),
        instruction_latencies=dict(data.get("instruction_latencies", {})),
        dump_registers=bool(data.get("dump_registers", True)),
        dump_memory_bytes=int(data.get("dump_memory_bytes", 0)),
    )
