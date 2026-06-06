"""Synthetic Databricks responses for MOCK_MODE.

Reads the JSON data pack shipped under the top-level ``data/`` folder so the
demo is fully deterministic and self-contained.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

# repo_root/data — this file lives at repo_root/src/app/mocks/databricks_mock.py
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@cache
def _load(name: str) -> list[dict] | dict:
    return json.loads((_DATA_DIR / name).read_text())


def candidates(facility: str) -> list[dict]:
    rows = _load("candidates.json")
    return [c for c in rows if c["facility"] == facility]


def history(sku: str) -> dict:
    # Deterministic pseudo-history derived from the SKU string so the value is
    # stable across runs without shipping a separate file.
    seed = sum(ord(ch) for ch in sku)
    return {
        "sku": sku,
        "avg_daily_velocity": round(8 + (seed % 12) + (seed % 7) / 10, 1),
        "stddev": round(1.5 + (seed % 5) / 2, 1),
        "trailing_days": 14,
    }
