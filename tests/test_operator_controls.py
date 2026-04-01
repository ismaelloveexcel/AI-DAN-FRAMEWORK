"""
Tests for operator console, approval gating, idempotency, and guardrails.
"""

import os
import importlib
import uuid

from fastapi.testclient import TestClient

from core.config import reload_settings


def _set_env(k: str, v: str) -> None:
    os.environ[k] = v


def _reset_env(saved):
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _load_client():
    os.environ["OPERATIONS_DB_PATH"] = f"/tmp/test_ops_controls_{uuid.uuid4().hex}.db"
    import api_server

    module = importlib.reload(api_server)
    return TestClient(module.app)


def test_operator_console_and_approval_flow():
    keys = [
        "ENABLE_AUTH",
        "FRAMEWORK_API_KEY",
        "APPROVAL_SCOPE",
        "AUTO_RETRY_MAX_ATTEMPTS",
        "AUTO_RETRY_BACKOFF_MS",
        "OPERATIONS_DB_PATH",
    ]
    saved = {k: os.environ.get(k) for k in keys}
    _set_env("ENABLE_AUTH", "true")
    _set_env("FRAMEWORK_API_KEY", "test-operator-key")
    _set_env("APPROVAL_SCOPE", "money,brand,legal")
    _set_env("AUTO_RETRY_MAX_ATTEMPTS", "1")
    _set_env("AUTO_RETRY_BACKOFF_MS", "0")
    reload_settings()

    client = _load_client()
    headers = {"X-API-Key": "test-operator-key", "Idempotency-Key": "op-approve-1"}

    response = client.post(
        "/sales/process-lead",
        json={
            "lead_name": "Solo Founder",
            "lead_email": "solo@example.com",
            "lead_company": "IndieCo",
            "lead_source": "manual",
        },
        headers=headers,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "approval_required"
    approval_id = body["approval"]["approval_id"]

    decision = client.post(
        "/operator/approve-and-run",
        json={"approval_id": approval_id, "approve": True, "decision_note": "ok"},
        headers={"X-API-Key": "test-operator-key", "Idempotency-Key": "approve-run-1"},
    )
    assert decision.status_code == 202
    job_id = decision.json()["job"]["id"]

    batch = client.post(
        "/operator/run-daily-batch",
        json={"limit": 10},
        headers={"X-API-Key": "test-operator-key", "Idempotency-Key": "batch-1"},
    )
    assert batch.status_code == 200

    job = client.get(f"/operator/jobs/{job_id}", headers={"X-API-Key": "test-operator-key"})
    assert job.status_code == 200
    assert job.json()["job"]["status"] in {"succeeded", "running", "pending", "dead_letter"}

    console = client.get("/operator/console", headers={"X-API-Key": "test-operator-key"})
    assert console.status_code == 200
    data = console.json()
    assert "primary_action" in data
    assert "kpis" in data

    _reset_env(saved)
    reload_settings()


def test_idempotency_replay():
    keys = ["ENABLE_AUTH", "FRAMEWORK_API_KEY", "APPROVAL_SCOPE", "OPERATIONS_DB_PATH"]
    saved = {k: os.environ.get(k) for k in keys}
    _set_env("ENABLE_AUTH", "true")
    _set_env("FRAMEWORK_API_KEY", "test-operator-key")
    _set_env("APPROVAL_SCOPE", "")
    reload_settings()

    client = _load_client()
    headers = {"X-API-Key": "test-operator-key", "Idempotency-Key": "idem-replay-1"}

    payload = {"topic": "idempotency", "depth": "medium"}
    first = client.post("/research", json=payload, headers=headers)
    second = client.post("/research", json=payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json() or second.json().get("idempotency", {}).get("replayed") is True

    _reset_env(saved)
    reload_settings()
