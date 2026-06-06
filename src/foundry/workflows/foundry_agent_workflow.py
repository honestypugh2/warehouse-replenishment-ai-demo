"""Agent Framework sequential workflow over the persistent Foundry agents.

This is the Foundry-native version of ``sequential_replen.run_local``. Instead of
a plain in-process loop, it builds a **Microsoft Agent Framework** sequential
workflow (Retriever → Validator → Recommender) and runs it. The Recommender step
narrates through the persistent Foundry recommender agent, so the run shows up in
the portal's Tracing / Monitoring tabs.

Governance is identical to every other path: candidates, validations, decisions,
and min/max numbers are deterministic (computed by the same local functions). The
workflow only changes *how* the steps are orchestrated and *where* the narration
runs — never the decision or the numbers.

Selection / fallback (see :func:`run_sequential`):
  1. ``FOUNDRY_USE_AGENTS=true`` and Agent Framework installed → run this
     Agent Framework workflow.
  2. otherwise → fall back to the in-process ``sequential_replen.run_local``.
"""

# NOTE: do NOT add ``from __future__ import annotations`` here. The Agent
# Framework handler validator inspects raw method annotations, so the
# ``WorkflowContext[...]`` annotations on the executors must be real generic
# aliases at definition time, not stringized.

import asyncio
from dataclasses import dataclass, field
from typing import Never

from app.config import settings
from app.models.schemas import (
    Candidate,
    Recommendation,
    SequentialRunResult,
    ValidationResult,
)
from foundry.agents import recommender_agent, retriever_agent, validator_agent
from foundry.workflows.sequential_replen import run_local


@dataclass
class _State:
    """State threaded through the workflow executors."""

    facility: str
    mode: str | None = None
    candidates: list[Candidate] = field(default_factory=list)
    validations: list[ValidationResult] = field(default_factory=list)


def _build_workflow():
    """Construct the Agent Framework sequential workflow (lazy AF imports)."""
    from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

    from foundry.observability import get_tracer

    tracer = get_tracer()

    class RetrieverExecutor(Executor):
        @handler
        async def run(self, state: _State, ctx: WorkflowContext[_State]) -> None:
            with tracer.start_as_current_span("agent.retriever") as span:
                state.candidates = retriever_agent.retrieve(state.facility)
                span.set_attribute("replen.facility", state.facility)
                span.set_attribute("replen.candidate_count", len(state.candidates))
            await ctx.send_message(state)

    class ValidatorExecutor(Executor):
        @handler
        async def run(self, state: _State, ctx: WorkflowContext[_State]) -> None:
            with tracer.start_as_current_span("agent.validator") as span:
                state.validations = [
                    validator_agent.validate(candidate) for candidate in state.candidates
                ]
                passed = sum(1 for v in state.validations if v.passed)
                span.set_attribute("replen.validated_passed", passed)
            await ctx.send_message(state)

    class RecommenderExecutor(Executor):
        @handler
        async def run(
            self, state: _State, ctx: WorkflowContext[Never, SequentialRunResult]
        ) -> None:
            with tracer.start_as_current_span("agent.recommender") as span:
                recommendations: list[Recommendation] = [
                    recommender_agent.reason(candidate, validation, state.mode)
                    for candidate, validation in zip(
                        state.candidates, state.validations, strict=True
                    )
                ]
                span.set_attribute("replen.recommendation_count", len(recommendations))
            await ctx.yield_output(
                SequentialRunResult(
                    facility=state.facility,
                    count=len(recommendations),
                    recommendations=recommendations,
                )
            )

    retriever = RetrieverExecutor(id="retriever")
    validator = ValidatorExecutor(id="validator")
    recommender = RecommenderExecutor(id="recommender")
    return (
        WorkflowBuilder(start_executor=retriever, output_from=[recommender])
        .add_chain([retriever, validator, recommender])
        .build()
    )


async def run_sequential_async(
    facility: str, mode: str | None = None
) -> SequentialRunResult:
    """Run the Agent Framework sequential workflow for one facility."""
    workflow = _build_workflow()
    result = await workflow.run(_State(facility=facility, mode=mode))
    outputs = result.get_outputs()
    if not outputs:
        raise RuntimeError("Agent Framework workflow produced no output.")
    return outputs[-1]


def run_sequential(facility: str, mode: str | None = None) -> SequentialRunResult:
    """Run the sequential pipeline, preferring the Agent Framework workflow.

    Falls back to the in-process ``run_local`` when persistent agents are disabled
    or Agent Framework is not installed, so the demo always runs.
    """
    if not settings.foundry_use_agents:
        return run_local(facility, mode)
    try:
        import agent_framework  # noqa: F401
    except ImportError:
        return run_local(facility, mode)
    return asyncio.run(run_sequential_async(facility, mode))
