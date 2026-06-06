"""Foundry mode resolution and live-narration plumbing.

These tests exercise the *wiring* of the live Foundry path without making any
real Azure call: the live reasoner is monkeypatched. They guarantee that:
  - decisions/citations are identical in mock and live modes;
  - live narration is delegated to the Foundry reasoner for non-reject items;
  - reject items always use the deterministic template (never the model);
  - 'live' is only honored when a project endpoint is configured.
"""

import pytest

import foundry.foundry_reasoner as foundry_reasoner
from app.config import settings
from app.models.schemas import Candidate, ValidationResult
from foundry import narration
from foundry.agents.recommender_agent import reason


def _candidate(confidence: float = 0.91) -> Candidate:
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


def test_resolve_mode_requires_endpoint(monkeypatch):
    monkeypatch.setattr(settings, "azure_foundry_project_endpoint", None)
    assert settings.resolve_foundry_mode("live") == "mock"
    assert settings.foundry_live_available is False


def test_resolve_mode_live_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "azure_foundry_project_endpoint", "https://x.ai")
    assert settings.resolve_foundry_mode("live") == "live"
    assert settings.resolve_foundry_mode(None) == "mock"  # default stays mock


def test_mock_narration_is_deterministic():
    candidate = _candidate()
    val = ValidationResult(sku=candidate.sku, passed=True)
    first = narration.narrate(candidate, val, "approve_suggested", "mock")
    second = narration.narrate(candidate, val, "approve_suggested", "mock")
    assert first == second
    assert "100/320" in first


def test_live_narration_delegates_to_foundry(monkeypatch):
    called = {}

    def fake_explain(candidate, validation, decision):
        called["hit"] = (candidate.sku, decision)
        return "LIVE explanation from Foundry."

    monkeypatch.setattr(foundry_reasoner, "explain", fake_explain)
    candidate = _candidate()
    val = ValidationResult(sku=candidate.sku, passed=True)
    text = narration.narrate(candidate, val, "approve_suggested", "live")
    assert text == "LIVE explanation from Foundry."
    assert called["hit"] == ("CHARD-750-12", "approve_suggested")


def test_live_reject_uses_template_not_model(monkeypatch):
    def boom(*_a, **_k):  # pragma: no cover - must never be called
        raise AssertionError("reject narration must not call Foundry")

    monkeypatch.setattr(foundry_reasoner, "explain", boom)
    candidate = _candidate()
    val = ValidationResult(
        sku=candidate.sku, passed=False, reasons=["wave conflict"], blocking_wave_id="WV-1"
    )
    text = narration.narrate(candidate, val, "reject", "live")
    assert "Blocked by validator" in text


def test_decision_is_mode_independent(monkeypatch):
    monkeypatch.setattr(foundry_reasoner, "explain", lambda *a, **k: "live text")
    monkeypatch.setattr(settings, "azure_foundry_project_endpoint", "https://x.ai")
    candidate = _candidate()
    val = ValidationResult(sku=candidate.sku, passed=True)
    mock_rec = reason(candidate, val, "mock")
    live_rec = reason(candidate, val, "live")
    assert mock_rec.decision == live_rec.decision == "approve_suggested"
    assert mock_rec.citations == live_rec.citations
    assert live_rec.explanation == "live text"
    assert mock_rec.explanation != live_rec.explanation


def test_live_reasoner_errors_without_dependencies(monkeypatch):
    """When live is misconfigured, the reasoner raises a clear, typed error."""
    monkeypatch.setattr(settings, "azure_foundry_project_endpoint", None)
    foundry_reasoner._client.cache_clear()
    with pytest.raises(foundry_reasoner.FoundryReasoningError):
        foundry_reasoner.explain(_candidate(), ValidationResult(sku="x", passed=True), "needs_review")
