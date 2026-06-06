"""Unit tests for the sequential and multi-agent workflows."""

from foundry.workflows.multiagent_replen import run_local as run_multi
from foundry.workflows.sequential_replen import run_local as run_seq


def test_sequential_nj01_counts():
    result = run_seq("NJ-01")
    assert result.facility == "NJ-01"
    assert result.count == 12
    rejected = [r.candidate.sku for r in result.recommendations if r.decision == "reject"]
    assert set(rejected) == {"CAB-750-12", "PROS-750-6"}
    passed = [r for r in result.recommendations if r.validation.passed]
    assert len(passed) == 10


def test_multiagent_ranks_and_caps_at_15():
    result = run_multi(["NJ-01", "CA-02"])
    assert result.facilities == ["NJ-01", "CA-02"]
    assert len(result.ranking) <= 15
    scores = [item.score for item in result.ranking]
    assert scores == sorted(scores, reverse=True)
    # Blocked SKUs never appear in the ranked plan.
    skus = {item.sku for item in result.ranking}
    assert "CAB-750-12" not in skus
    assert "PROS-750-6" not in skus
