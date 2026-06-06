"""Pydantic data contracts shared across services, routes, and workflows."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Decision = Literal["approve_suggested", "needs_review", "reject"]


class Candidate(BaseModel):
    """A min-max candidate produced by Databricks (the system of intelligence)."""

    sku: str
    facility: str
    location: str
    current_min: int
    current_max: int
    recommended_min: int
    recommended_max: int
    rationale: str
    confidence: float = Field(ge=0, le=1)


class ValidationResult(BaseModel):
    """Deterministic operational validation against live D365 state."""

    sku: str
    passed: bool
    reasons: list[str] = []
    blocking_wave_id: str | None = None
    blocking_orders: list[str] = []


class Recommendation(BaseModel):
    """A validated, reasoned, and citation-grounded recommendation."""

    candidate: Candidate
    validation: ValidationResult
    decision: Decision
    explanation: str
    citations: list[str] = []


class SequentialRunResult(BaseModel):
    facility: str
    count: int
    recommendations: list[Recommendation]


class RankedItem(BaseModel):
    facility: str
    sku: str
    score: float
    decision: Decision
    explanation: str
    citations: list[str] = []


class MultiAgentRunResult(BaseModel):
    facilities: list[str]
    ranking: list[RankedItem]


class ApprovalRequest(BaseModel):
    """Payload posted from the Teams approval card / frontend."""

    sku: str
    facility: str
    new_min: int
    new_max: int
    approver_upn: str
    rationale: str


class D365WriteResponse(BaseModel):
    sku: str
    facility: str
    success: bool
    audit_id: str
    message: str


class RejectionRequest(BaseModel):
    sku: str
    facility: str
    approver_upn: str
    reason: str


class RejectionResponse(BaseModel):
    sku: str
    facility: str
    deferred: bool
    audit_id: str
    message: str
