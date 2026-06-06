"""Unit tests for the Operational Validator agent."""

from app.models.schemas import Candidate
from foundry.agents.validator_agent import validate


def _candidate(sku: str, facility: str = "NJ-01") -> Candidate:
    return Candidate(
        sku=sku,
        facility=facility,
        location="PM-A12",
        current_min=60,
        current_max=240,
        recommended_min=120,
        recommended_max=360,
        rationale="test",
        confidence=0.9,
    )


def test_blocks_sku_on_active_wave():
    result = validate(_candidate("CAB-750-12"))
    assert result.passed is False
    assert result.blocking_wave_id == "WV-2026-06-05-014"
    assert "SO-100455" in result.blocking_orders


def test_passes_sku_without_wave_conflict():
    result = validate(_candidate("CHARD-750-12"))
    assert result.passed is True
    assert result.blocking_wave_id is None
    assert result.reasons == []
