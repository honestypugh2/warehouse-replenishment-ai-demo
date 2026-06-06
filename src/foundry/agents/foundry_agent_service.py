"""Persistent Foundry agents (Microsoft Foundry — new Agents experience).

This module creates and invokes **persistent prompt agents** in the Foundry
project using the GA ``azure-ai-projects`` SDK (>= 2.0). Agents are published as
versioned ``PromptAgentDefinition`` resources via ``agents.create_version`` and
invoked over the OpenAI **Responses** protocol with an ``agent_reference``. This
is the *New Foundry* agent model — not the legacy Assistants API (``asst_`` ids),
which New Foundry no longer supports.

Unlike the in-process Python agents (``recommender_agent`` et al., which are the
default offline fallback), these agents are registered server-side, so they:

* appear in the **Agents** list of the Foundry portal for the project, and
* emit responses + GenAI traces that show up in the portal **Tracing** and
  **Monitoring** tabs (via the Application Insights connection wired in infra).

Governance is preserved: the agents never decide and never change numbers. The
deterministic decision + min/max are computed locally (``recommender_agent``)
and passed *into* the agent as grounded facts, exactly like the chat path. Only
the natural-language narration is produced by the agent.

The agents are provisioned by ``scripts/provision_foundry_agents.py`` and used at
runtime when ``FOUNDRY_USE_AGENTS=true``. If the SDK is missing, the endpoint is
unset, or the agent has not been provisioned, callers fall back to the raw chat
path and then to the deterministic mock template.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

from app.config import settings
from app.models.schemas import Candidate, ValidationResult

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

# Agent name prefix keeps the demo's agents grouped + discoverable in the portal.
_PREFIX = "replen"


class FoundryAgentError(RuntimeError):
    """Raised when a persistent Foundry agent cannot be provisioned or invoked."""


@dataclass(frozen=True)
class AgentSpec:
    """Definition of one persistent Foundry agent."""

    role: str
    name: str
    prompt_file: str
    description: str


# The demo's agent roster. ``recommender`` is the agent invoked for live
# narration; the others persist so the portal + UI reflect the full pipeline and
# the Agent Framework workflow can orchestrate them.
AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec(
        role="retriever",
        name=f"{_PREFIX}-retriever",
        prompt_file="retriever.system.md",
        description="Pulls replenishment candidates from Databricks (mocked).",
    ),
    AgentSpec(
        role="validator",
        name=f"{_PREFIX}-validator",
        prompt_file="validator.system.md",
        description="Checks each candidate against D365 wave/policy state (mocked).",
    ),
    AgentSpec(
        role="recommender",
        name=f"{_PREFIX}-recommender",
        prompt_file="recommender.system.md",
        description="Explains and grounds each validated min/max recommendation.",
    ),
)

_SPEC_BY_ROLE = {spec.role: spec for spec in AGENT_SPECS}


def _instructions(spec: AgentSpec) -> str:
    return (_PROMPTS / spec.prompt_file).read_text(encoding="utf-8")


@cache
def _project_client():
    """Build (and cache) a Foundry project client for the project."""
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:  # pragma: no cover - only in live agent mode
        raise FoundryAgentError(
            "Persistent Foundry agents need azure-ai-projects + azure-identity. "
            "Install them with: uv pip install -r requirements-prod.txt"
        ) from exc

    if not settings.azure_foundry_project_endpoint:
        raise FoundryAgentError(
            "AZURE_FOUNDRY_PROJECT_ENDPOINT is not set; cannot reach the agents."
        )

    return AIProjectClient(
        endpoint=settings.azure_foundry_project_endpoint,
        credential=DefaultAzureCredential(),
    )


def _agent_definition(spec: AgentSpec):
    """Build the prompt-agent definition for one spec."""
    from azure.ai.projects.models import PromptAgentDefinition

    return PromptAgentDefinition(
        model=settings.azure_foundry_model_deployment,
        instructions=_instructions(spec),
        temperature=0.2,
    )


def provision_agents() -> dict[str, str]:
    """Create (or version) every persistent agent. Idempotent by agent name.

    Returns a mapping of ``role -> agent_name``. Safe to re-run: calling
    ``create_version`` again publishes a new version under the same agent name
    rather than creating a duplicate agent.
    """
    client = _project_client()
    result: dict[str, str] = {}
    for spec in AGENT_SPECS:
        agent = client.agents.create_version(
            agent_name=spec.name,
            definition=_agent_definition(spec),
            description=spec.description,
        )
        result[spec.role] = agent.name
    return result


@cache
def _agent_name(role: str) -> str:
    """Resolve a provisioned agent name by role (verified against the project)."""
    spec = _SPEC_BY_ROLE.get(role)
    if spec is None:
        raise FoundryAgentError(f"Unknown agent role: {role}")

    client = _project_client()
    try:
        client.agents.get(spec.name)
    except Exception as exc:  # noqa: BLE001 - surface as a fallback-able error
        raise FoundryAgentError(
            f"Agent '{spec.name}' is not provisioned. Run: "
            "python scripts/provision_foundry_agents.py"
        ) from exc
    return spec.name


def narrate_with_agent(
    candidate: Candidate, validation: ValidationResult, decision: str
) -> str:
    """Produce the live narration via the persistent recommender agent.

    Runs a single grounded turn against the agent over the OpenAI **Responses**
    protocol (``agent_reference``) and returns its text. Raises
    :class:`FoundryAgentError` if the agent path is unavailable so the caller can
    fall back to the chat-completion path.
    """
    # Local import keeps foundry_reasoner the single source of the prompt text.
    from foundry.foundry_reasoner import build_user_prompt

    client = _project_client()
    agent_name = _agent_name("recommender")

    try:
        with client.get_openai_client() as openai_client:
            response = openai_client.responses.create(
                input=build_user_prompt(candidate, validation, decision),
                extra_body={
                    "agent_reference": {
                        "name": agent_name,
                        "type": "agent_reference",
                    }
                },
            )
    except Exception as exc:  # noqa: BLE001 - any failure falls back to chat path
        raise FoundryAgentError(f"Agent run failed: {exc}") from exc

    text = (response.output_text or "").strip()
    if not text:
        raise FoundryAgentError("Agent returned no text response.")
    return text
