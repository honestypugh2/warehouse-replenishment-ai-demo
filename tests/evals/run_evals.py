"""Evaluation harness.

Runs the groundedness and decision-quality checks described in
``src/foundry/evaluations/*.yaml`` against the sequential workflow and reports a
pass/fail summary. Invoked by CI:  ``uv run python -m tests.evals.run_evals``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the src-layout packages importable when run standalone (python -m ...).
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from app.mocks import databricks_mock  # noqa: E402
from foundry.workflows.sequential_replen import run_local  # noqa: E402

FACILITY = "NJ-01"
EXPECTED_REJECTED = {"CAB-750-12", "PROS-750-6"}
HIGH_CONFIDENCE = 0.80


def _source_index() -> dict[str, dict]:
    return {row["sku"]: row for row in databricks_mock.candidates(FACILITY)}


def evaluate() -> list[tuple[str, bool, str]]:
    result = run_local(FACILITY)
    recs = result.recommendations
    source = _source_index()
    checks: list[tuple[str, bool, str]] = []

    # --- groundedness -------------------------------------------------
    checks.append(
        (
            "groundedness.has_databricks_citation",
            all(any(c.startswith("databricks://") for c in r.citations) for r in recs),
            "every recommendation cites a Databricks candidate",
        )
    )
    checks.append(
        (
            "groundedness.has_d365_citation",
            all(any(c.startswith("d365://") for c in r.citations) for r in recs),
            "every recommendation cites D365 state",
        )
    )
    checks.append(
        (
            "groundedness.no_fabricated_values",
            all(
                r.candidate.recommended_min == source[r.candidate.sku]["recommended_min"]
                and r.candidate.recommended_max == source[r.candidate.sku]["recommended_max"]
                for r in recs
            ),
            "recommended values are never altered by the reasoner",
        )
    )

    # --- decision quality ---------------------------------------------
    checks.append(
        (
            "decision_quality.blocks_active_wave_skus",
            all(
                r.decision == "reject"
                for r in recs
                if r.candidate.sku in EXPECTED_REJECTED
            ),
            "all SKUs on an active wave are rejected",
        )
    )
    checks.append(
        (
            "decision_quality.confidence_policy",
            all(
                (r.decision == "approve_suggested")
                == (r.candidate.confidence >= HIGH_CONFIDENCE)
                for r in recs
                if r.validation.passed
            ),
            "passing candidates follow the confidence policy",
        )
    )
    return checks


def main() -> int:
    checks = evaluate()
    passed = 0
    for name, ok, desc in checks:
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {name} — {desc}")
        passed += ok
    total = len(checks)
    print(f"\n{passed}/{total} checks passed.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
