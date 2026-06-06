"""Synthetic D365 F&O operational state for MOCK_MODE."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

# repo_root/data — this file lives at repo_root/src/app/mocks/d365_mock.py
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


@cache
def _load(name: str) -> list[dict]:
    return json.loads((_DATA_DIR / name).read_text())


def open_orders(sku: str) -> list[dict]:
    return [o for o in _load("orders.json") if o["sku"] == sku and o["status"] == "open"]


def active_waves(facility: str) -> list[dict]:
    return [
        w
        for w in _load("waves.json")
        if w["facility"] == facility and w["status"] == "active"
    ]


def capacity(location: str) -> dict | None:
    return next((c for c in _load("capacity.json") if c["location"] == location), None)
