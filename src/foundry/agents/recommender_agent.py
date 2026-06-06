"""Recommendation Reasoner agent — ranks, explains, and grounds each candidate.

The reasoner does not invent min-max values. It classifies each validated
candidate into a decision and produces a human-readable explanation plus
citation ids that trace back to Databricks and D365.

The *decision* and *citations* are deterministic (pure ``decide``). The
*explanation* is produced by ``narration.narrate`` and depends on the Foundry
mode: a local template (``mock``) or a real Foundry model (``live``).
"""

from __future__ import annotations

from app.config import settings
from app.models.schemas import Candidate, Recommendation, ValidationResult
from foundry.narration import narrate

HIGH_CONFIDENCE = 0.80


def decide(
    candidate: Candidate, validation: ValidationResult
) -> tuple[str, list[str]]:
    """Deterministic decision + citations. Identical in mock and live modes."""
    citations = [
        f"databricks://candidates/{candidate.facility}/{candidate.sku}",
        f"d365://waves/{candidate.facility}",
    ]

    if not validation.passed:
        decision = "reject"
        if validation.blocking_wave_id:
            citations.append(f"d365://waves/{validation.blocking_wave_id}")
    elif candidate.confidence >= HIGH_CONFIDENCE:
        decision = "approve_suggested"
    else:
        decision = "needs_review"

    return decision, citations


def reason(
    candidate: Candidate,
    validation: ValidationResult,
    mode: str | None = None,
) -> Recommendation:
    decision, citations = decide(candidate, validation)
    effective_mode = settings.resolve_foundry_mode(mode)
    explanation = narrate(candidate, validation, decision, effective_mode)

    return Recommendation(
        candidate=candidate,
        validation=validation,
        decision=decision,  # type: ignore[arg-type]
        explanation=explanation,
        citations=citations,
    )
