"""Unit tests for the Recommendation Reasoner decision policy."""

import pytest

from app.models.schemas import Candidate, ValidationResult
from foundry.agents.recommender_agent import reason


def _candidate(confidence: float) -> Candidate:
    return Candidate(
        sku="CHARD-750-12",
        facility="NJ-01",
        location="PM-A14",
        current_min=90,
        current_max=300,
        recommended_min=100,
        recommended_max=320,
        rationale="test",
        confidence=confidence,
    )


def test_failed_validation_yields_reject():
    val = ValidationResult(
        sku="CAB-750-12", passed=False, reasons=["wave conflict"], blocking_wave_id="WV-1"
    )
    rec = reason(_candidate(0.95), val)
    assert rec.decision == "reject"


@pytest.mark.parametrize(
    "confidence,expected",
    [(0.80, "approve_suggested"), (0.95, "approve_suggested"), (0.79, "needs_review"), (0.5, "needs_review")],
)
def test_confidence_policy(confidence: float, expected: str):
    val = ValidationResult(sku="CHARD-750-12", passed=True)
    rec = reason(_candidate(confidence), val)
    assert rec.decision == expected


def test_citations_present():
    val = ValidationResult(sku="CHARD-750-12", passed=True)
    rec = reason(_candidate(0.9), val)
    assert any(c.startswith("databricks://") for c in rec.citations)
    assert any(c.startswith("d365://") for c in rec.citations)
