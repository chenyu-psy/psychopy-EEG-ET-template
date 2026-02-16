"""Data I/O helpers for Experiment 1."""

from __future__ import annotations

import csv
from pathlib import Path


def init_data_file(path: Path, condition_columns: list[str]) -> list[str]:
    """Create/overwrite data CSV and write header."""
    fields = ["subject", "block_id", "trial_id", *condition_columns, "label", "symbol", "resp", "rt_ms"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
    return fields


def append_trial(path: Path, row: dict, fields: list[str]) -> None:
    """Append one trial row to data CSV."""
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writerow(row)
