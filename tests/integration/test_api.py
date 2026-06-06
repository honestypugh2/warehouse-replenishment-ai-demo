"""Integration tests for the FastAPI endpoints (MOCK_MODE)."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


@pytest.fixture
def foundry_unconfigured(monkeypatch):
    """Force the 'live Foundry not configured' state regardless of ambient .env."""
    monkeypatch.setattr(settings, "azure_foundry_project_endpoint", "")
    monkeypatch.setattr(settings, "foundry_mode", "mock")


def test_health(foundry_unconfigured):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["mock_mode"] is True
    # Data systems are always mocked; Foundry defaults to mock and live is off.
    assert body["databricks_mode"] == "mock"
    assert body["d365_mode"] == "mock"
    assert body["foundry_mode"] == "mock"
    assert body["foundry_live_available"] is False


def test_sequential_explicit_mock_mode():
    res = client.get(
        "/recommendations/sequential",
        params={"facility": "NJ-01", "foundry": "mock"},
    )
    assert res.status_code == 200
    assert res.json()["count"] == 12


def test_live_mode_rejected_when_not_configured(foundry_unconfigured):
    res = client.get(
        "/recommendations/sequential",
        params={"facility": "NJ-01", "foundry": "live"},
    )
    assert res.status_code == 400
    assert "not configured" in res.json()["detail"]


def test_sequential_endpoint():
    res = client.get("/recommendations/sequential", params={"facility": "NJ-01"})
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 12
    assert len(body["recommendations"]) == 12


def test_multiagent_endpoint():
    res = client.get(
        "/recommendations/multiagent", params=[("facilities", "NJ-01"), ("facilities", "CA-02")]
    )
    assert res.status_code == 200
    body = res.json()
    assert body["facilities"] == ["NJ-01", "CA-02"]
    assert len(body["ranking"]) <= 15


def test_validate_endpoint_blocked_sku():
    res = client.get("/validate", params={"facility": "NJ-01", "sku": "CAB-750-12"})
    assert res.status_code == 200
    body = res.json()
    assert body["passed"] is False
    assert body["blocking_wave_id"] == "WV-2026-06-05-014"


def test_approve_writes_with_audit_id():
    payload = {
        "sku": "CHARD-750-12",
        "facility": "NJ-01",
        "new_min": 100,
        "new_max": 320,
        "approver_upn": "planner@contoso.com",
        "rationale": "approved in test",
    }
    res = client.post("/approve", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["audit_id"].startswith("AUDIT-")


def test_approve_rejects_invalid_range():
    payload = {
        "sku": "CHARD-750-12",
        "facility": "NJ-01",
        "new_min": 100,
        "new_max": 50,
        "approver_upn": "planner@contoso.com",
        "rationale": "bad range",
    }
    res = client.post("/approve", json=payload)
    assert res.status_code == 400


def test_reject_endpoint_defers():
    payload = {
        "sku": "CAB-750-12",
        "facility": "NJ-01",
        "approver_upn": "planner@contoso.com",
        "reason": "active wave",
    }
    res = client.post("/approve/reject", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["deferred"] is True
    assert body["audit_id"].startswith("AUDIT-")
