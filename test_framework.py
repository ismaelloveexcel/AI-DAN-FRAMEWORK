#!/usr/bin/env python3
"""
AIDAN-OS — Validation tests for the lean API server.
Compatible with pytest for CI/CD pipelines.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("USE_MOCK_KB", "true")


# ---------------------------------------------------------------------------
# Core import tests
# ---------------------------------------------------------------------------

def test_api_server_importable():
    """api_server.py must be importable (re-exports app from api.server)."""
    import api_server
    assert hasattr(api_server, "app")


def test_aidan_server_app():
    """api.server must expose a FastAPI app."""
    from api.server import app
    assert app is not None
    assert app.title == "AIDAN-OS API"


def test_core_imports():
    """Core modules that are kept must import cleanly."""
    from core import config  # noqa: F401
    from core import exceptions  # noqa: F401
    from core import http_client  # noqa: F401
    from core import llm  # noqa: F401


def test_executive_chat_importable():
    """Executive chat agent must import without error."""
    from agents.executive_chat import ExecutiveChatAgent
    agent = ExecutiveChatAgent()
    assert agent is not None


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

def test_health_endpoint():
    """GET /health must return 200 with status ok."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "AIDAN-OS"


# ---------------------------------------------------------------------------
# AIDAN endpoints (mock mode — no OpenAI key required)
# ---------------------------------------------------------------------------

def test_aidan_chat_endpoint():
    """POST /aidan/chat must return a response (mock mode)."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.post("/aidan/chat", json={"message": "What should I do today?"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "timestamp" in data


def test_aidan_daily_endpoint():
    """POST /aidan/daily must return a daily focus."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.post(
        "/aidan/daily",
        json={"current_product": "CareerScore MU", "current_stage": "Building"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "daily_focus" in data
    assert data["product"] == "CareerScore MU"


def test_aidan_evaluate_endpoint():
    """POST /aidan/evaluate must return an evaluation."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.post(
        "/aidan/evaluate",
        json={"idea": "AI CV scoring tool for Mauritius job seekers"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "evaluation" in data
    assert data["idea"] != ""


def test_aidan_build_prompt_endpoint():
    """POST /aidan/build-prompt must return a Cursor prompt."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.post(
        "/aidan/build-prompt",
        json={
            "idea": "CV scoring tool",
            "core_feature": "Paste CV → get score and gaps",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "cursor_prompt" in data


def test_aidan_weekly_review_endpoint():
    """POST /aidan/weekly-review must return a weekly review."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.post(
        "/aidan/weekly-review",
        json={"week_number": 1, "mrr": 0.0, "users": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "review" in data
    assert data["week"] == 1
    assert data["mrr_gap"] == 500.0


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

def test_auth_disabled_by_default():
    """Auth must be disabled by default so CI passes without keys."""
    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    # Without API key, should still succeed (ENABLE_AUTH=false by default)
    response = client.post("/aidan/chat", json={"message": "hello"})
    assert response.status_code == 200


def test_auth_rejects_bad_key_when_enabled(monkeypatch):
    """When ENABLE_AUTH=true, wrong key should return 403."""
    monkeypatch.setenv("ENABLE_AUTH", "true")
    monkeypatch.setenv("FRAMEWORK_API_KEY", "secret-key")

    from fastapi.testclient import TestClient
    from api.server import app

    client = TestClient(app)
    response = client.post(
        "/aidan/chat",
        json={"message": "hello"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("AIDAN-OS — Validation Tests")
    print("=" * 60)
    return pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    sys.exit(main())
