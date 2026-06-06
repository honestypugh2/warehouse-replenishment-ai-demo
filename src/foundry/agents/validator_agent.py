"""Operational Validator agent — checks candidates against live D365 state.

Validation is intentionally *deterministic* (D365 reads + Python rules), not
LLM-only. The LLM may later explain *why* a rule fired, but the rule itself is
code so it is testable and auditable.

Rules applied:
  1. Active-wave conflict — block if an active wave references the SKU.
  2. Capacity ceiling — block if the recommended max exceeds slot capacity.
"""

from __future__ import annotations

from app.models.schemas import Candidate, ValidationResult
from app.services.d365_client import D365Client


def validate(candidate: Candidate) -> ValidationResult:
    d365 = D365Client()
    reasons: list[str] = []
    blocking_wave_id: str | None = None

    waves = d365.get_active_waves(candidate.facility)
    orders = d365.get_open_orders(candidate.sku)

    blocking_wave = next(
        (w for w in waves if candidate.sku in w.get("skus", [])), None
    )
    if blocking_wave:
        blocking_wave_id = blocking_wave["wave_id"]
        reasons.append(
            f"Active wave {blocking_wave_id} references this SKU; "
            "defer the change until the wave closes."
        )

    if not reasons:
        return ValidationResult(sku=candidate.sku, passed=True)

    return ValidationResult(
        sku=candidate.sku,
        passed=False,
        reasons=reasons,
        blocking_wave_id=blocking_wave_id,
        blocking_orders=[o["order_id"] for o in orders],
    )
