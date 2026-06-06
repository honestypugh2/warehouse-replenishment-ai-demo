"""Live Foundry reasoning.

Generates the natural-language explanation for a validated candidate using a
real **Azure AI Foundry** model deployment. This is the only place the demo
talks to a live Azure model; everything else (Databricks signals, D365 state)
stays mocked.

Governance note: this module never changes a *decision* or a *number*. It only
turns already-decided, already-grounded facts into a business-readable sentence.
The deterministic decision policy lives in ``recommender_agent`` and is identical
in mock and live modes.

Requires the production dependencies (see ``requirements-prod.txt``):
    azure-ai-projects, azure-identity, openai
and ``AZURE_FOUNDRY_PROJECT_ENDPOINT`` pointing at a Foundry project with the
configured model deployment.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from app.config import settings
from app.models.schemas import Candidate, ValidationResult

_PROMPT = Path(__file__).resolve().parent / "prompts" / "recommender.system.md"


class FoundryReasoningError(RuntimeError):
    """Raised when live Foundry reasoning cannot be produced."""


@cache
def _system_prompt() -> str:
    return _PROMPT.read_text(encoding="utf-8")


def system_prompt() -> str:
    """Public accessor for the Recommendation Reasoner system prompt."""
    return _system_prompt()


@cache
def _client():
    """Build (and cache) an Azure OpenAI client bound to the Foundry project.

    Uses Entra ID auth via ``DefaultAzureCredential`` — no keys in the demo.
    """
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - exercised only in live mode
        raise FoundryReasoningError(
            "Live Foundry reasoning needs the production dependencies. Install "
            "them with: uv pip install -r requirements-prod.txt"
        ) from exc

    if not settings.azure_foundry_project_endpoint:
        raise FoundryReasoningError(
            "AZURE_FOUNDRY_PROJECT_ENDPOINT is not set; cannot run live Foundry."
        )

    project = AIProjectClient(
        endpoint=settings.azure_foundry_project_endpoint,
        credential=DefaultAzureCredential(),
    )
    return project.get_openai_client()


def build_user_prompt(
    candidate: Candidate, validation: ValidationResult, decision: str
) -> str:
    """Grounded user prompt shared by the chat and the persistent-agent paths."""
    return (
        "Write ONE or TWO sentences, business-readable, grounded ONLY in the "
        "facts below. Do not invent or alter any numbers.\n\n"
        f"Facility: {candidate.facility}\n"
        f"SKU: {candidate.sku}\n"
        f"Decision (already made by policy): {decision}\n"
        f"Confidence: {candidate.confidence:.0%}\n"
        f"Current min/max: {candidate.current_min}/{candidate.current_max}\n"
        f"Recommended min/max: {candidate.recommended_min}/{candidate.recommended_max}\n"
        f"Databricks rationale: {candidate.rationale}\n"
        f"Validator passed: {validation.passed}\n"
        f"Validator reasons: {' '.join(validation.reasons) or 'none'}\n"
    )


def _explain_via_chat(
    candidate: Candidate, validation: ValidationResult, decision: str
) -> str:
    """Narration via a raw chat completion against the model deployment."""
    client = _client()
    completion = client.chat.completions.create(
        model=settings.azure_foundry_model_deployment,
        temperature=0.2,
        max_tokens=160,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": build_user_prompt(candidate, validation, decision)},
        ],
    )
    text = (completion.choices[0].message.content or "").strip()
    if not text:
        raise FoundryReasoningError("Foundry returned an empty explanation.")
    return text


def explain(candidate: Candidate, validation: ValidationResult, decision: str) -> str:
    """Return a Foundry-generated explanation for the (already-decided) candidate.

    When ``FOUNDRY_USE_AGENTS`` is enabled, narration is produced by a persistent
    Foundry agent (visible in the portal, traced in Application Insights). If that
    path is unavailable the call falls back to a raw chat completion. ``reject``
    candidates never reach this function — their wording is deterministic.
    """
    try:
        if settings.foundry_use_agents:
            try:
                from foundry.agents.foundry_agent_service import (
                    FoundryAgentError,
                    narrate_with_agent,
                )

                return narrate_with_agent(candidate, validation, decision)
            except FoundryAgentError:
                # Agent path unavailable (not provisioned / SDK missing) — fall
                # back to the direct chat-completion path below.
                pass
        return _explain_via_chat(candidate, validation, decision)
    except FoundryReasoningError:
        raise
    except Exception as exc:  # pragma: no cover - network/SDK errors at runtime
        raise FoundryReasoningError(f"Live Foundry call failed: {exc}") from exc

