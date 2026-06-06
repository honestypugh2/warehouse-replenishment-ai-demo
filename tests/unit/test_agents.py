"""Coverage for every Foundry agent: retriever, validator, recommender,
writer, and the multi-agent orchestrator.

(The validator and recommender decision policy also have focused tests in
``test_validator.py`` and ``test_recommender.py``; this module ensures each
agent in the pipeline is exercised end to end in mock mode.)
"""

import pytest

from app.models.schemas import ApprovalRequest, Candidate, ValidationResult
from foundry.agents import (
    orchestrator_agent,
    recommender_agent,
    retriever_agent,
    validator_agent,
    writer_agent,
)


# --- retriever ---------------------------------------------------------------
def test_retriever_returns_candidates_for_facility():
    candidates = retriever_agent.retrieve("NJ-01")
    assert len(candidates) == 12
    assert all(isinstance(c, Candidate) for c in candidates)
    assert all(c.facility == "NJ-01" for c in candidates)


def test_retriever_isolates_facilities():
    nj = retriever_agent.retrieve("NJ-01")
    ca = retriever_agent.retrieve("CA-02")
    assert len(ca) == 6
    assert {c.sku for c in nj}.isdisjoint([]) and len(nj) + len(ca) == 18


# --- validator ---------------------------------------------------------------
def test_validator_pure_rule():
    blocked = validator_agent.validate(
        Candidate(
            sku="CAB-750-12",
            facility="NJ-01",
            location="PM-A12",
            current_min=60,
            current_max=240,
            recommended_min=120,
            recommended_max=360,
            rationale="t",
            confidence=0.9,
        )
    )
    assert blocked.passed is False
    assert blocked.blocking_wave_id == "WV-2026-06-05-014"


# --- recommender -------------------------------------------------------------
def test_recommender_decide_is_pure():
    candidate = Candidate(
        sku="CHARD-750-12",
        facility="NJ-01",
        location="PM-A14",
        current_min=90,
        current_max=300,
        recommended_min=100,
        recommended_max=320,
        rationale="test",
        confidence=0.91,
    )
    validation = ValidationResult(sku="CHARD-750-12", passed=True)
    decision, citations = recommender_agent.decide(candidate, validation)
    assert decision == "approve_suggested"
    assert any(c.startswith("databricks://") for c in citations)


# --- writer ------------------------------------------------------------------
def test_writer_returns_audit_id():
    resp = writer_agent.write(
        ApprovalRequest(
            sku="CHARD-750-12",
            facility="NJ-01",
            new_min=100,
            new_max=320,
            approver_upn="planner@contoso.com",
            rationale="approved in test",
        )
    )
    assert resp.success is True
    assert resp.audit_id


def test_writer_rejects_invalid_range():
    with pytest.raises(ValueError):
        writer_agent.write(
            ApprovalRequest(
                sku="CHARD-750-12",
                facility="NJ-01",
                new_min=300,
                new_max=100,
                approver_upn="planner@contoso.com",
                rationale="bad range",
            )
        )


# --- orchestrator ------------------------------------------------------------
def test_orchestrator_ranks_and_caps():
    result = orchestrator_agent.orchestrate(["NJ-01", "CA-02"])
    assert result.facilities == ["NJ-01", "CA-02"]
    assert len(result.ranking) <= 15
    scores = [item.score for item in result.ranking]
    assert scores == sorted(scores, reverse=True)
    # Rejected (blocked) SKUs never appear in the ranked plan.
    assert all(item.decision != "reject" for item in result.ranking)
