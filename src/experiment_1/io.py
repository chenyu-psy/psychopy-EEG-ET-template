"""Data I/O helpers for Experiment 1."""

from __future__ import annotations

import csv
from pathlib import Path


FIELDS = ["subject", "trial", "symbol", "resp", "rt_ms"]


def init_data_file(path: Path) -> None:
    """Create/overwrite data CSV and write header."""
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()


def append_trial(path: Path, row: dict) -> None:
    """Append one trial row to data CSV."""
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writerow(row)
