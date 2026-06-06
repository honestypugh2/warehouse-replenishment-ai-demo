"""Narration — turns a decided, grounded candidate into a readable explanation.

Two implementations, selected by ``mode``:

* ``mock`` — a deterministic template. Fully offline, identical every run.
* ``live`` — a real Azure AI Foundry model (see ``foundry_reasoner``).

In both modes the *decision* and the *numbers* are fixed before narration runs,
so guardrails and evaluation results are mode-independent. ``reject`` candidates
always use the deterministic template (their wording is evidence, not prose).
"""

from __future__ import annotations

from app.models.schemas import Candidate, ValidationResult


def _mock_narrate(
    candidate: Candidate, validation: ValidationResult, decision: str
) -> str:
    if decision == "reject":
        return f"Blocked by validator: {' '.join(validation.reasons)}"
    if decision == "approve_suggested":
        return (
            f"High-confidence change ({candidate.confidence:.0%}). "
            f"{candidate.rationale} Proposed min-max "
            f"{candidate.recommended_min}/{candidate.recommended_max} "
            f"(was {candidate.current_min}/{candidate.current_max})."
        )
    return (
        f"Moderate confidence ({candidate.confidence:.0%}). "
        f"{candidate.rationale} Recommend a quick human check before applying "
        f"{candidate.recommended_min}/{candidate.recommended_max}."
    )


def narrate(
    candidate: Candidate,
    validation: ValidationResult,
    decision: str,
    mode: str = "mock",
) -> str:
    """Return the explanation text for a candidate under the given mode."""
    if mode == "live" and decision != "reject":
        from foundry.foundry_reasoner import explain

        return explain(candidate, validation, decision)
    return _mock_narrate(candidate, validation, decision)
