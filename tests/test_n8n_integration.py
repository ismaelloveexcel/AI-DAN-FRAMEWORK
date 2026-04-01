"""
AIDAN-OS — Integration tests for the lean API server.

Replaces the former n8n / sales / marketing integration tests.
All tests run in mock mode (no OpenAI key or external services required).
"""

import os
import pytest

os.environ.setdefault("USE_MOCK_KB", "true")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from api.server import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "AIDAN-OS"
        assert "timestamp" in data

    def test_health_no_auth_needed(self, client):
        """Health endpoint must never require authentication."""
        response = client.get("/health", headers={"X-API-Key": ""})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class TestAidanChat:
    def test_chat_returns_response(self, client):
        response = client.post("/aidan/chat", json={"message": "What should I do today?"})
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0

    def test_chat_with_context(self, client):
        response = client.post(
            "/aidan/chat",
            json={
                "message": "Should I build a new feature?",
                "context": "Currently at $0 MRR, building CareerScore MU",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_chat_returns_timestamp(self, client):
        response = client.post("/aidan/chat", json={"message": "hello"})
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# Daily Focus
# ---------------------------------------------------------------------------

class TestAidanDaily:
    def test_daily_returns_focus(self, client):
        response = client.post(
            "/aidan/daily",
            json={"current_product": "CareerScore MU", "current_stage": "Building"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "daily_focus" in data
        assert data["product"] == "CareerScore MU"
        assert data["stage"] == "Building"

    def test_daily_default_product(self, client):
        response = client.post("/aidan/daily", json={})
        assert response.status_code == 200
        data = response.json()
        assert "daily_focus" in data


# ---------------------------------------------------------------------------
# Idea Evaluation
# ---------------------------------------------------------------------------

class TestAidanEvaluate:
    def test_evaluate_returns_verdict(self, client):
        response = client.post(
            "/aidan/evaluate",
            json={"idea": "AI CV scoring tool for Mauritius job seekers"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "evaluation" in data
        assert data["idea"] == "AI CV scoring tool for Mauritius job seekers"

    def test_evaluate_with_custom_market(self, client):
        response = client.post(
            "/aidan/evaluate",
            json={"idea": "Budget tracking app", "target_market": "Mauritius SMBs"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "evaluation" in data
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# Build Prompt
# ---------------------------------------------------------------------------

class TestAidanBuildPrompt:
    def test_build_prompt_returns_cursor_prompt(self, client):
        response = client.post(
            "/aidan/build-prompt",
            json={
                "idea": "CareerScore MU",
                "core_feature": "Paste CV → get AI score + gaps",
                "tech_stack": "Static HTML + OpenAI API",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "cursor_prompt" in data
        assert data["idea"] == "CareerScore MU"

    def test_build_prompt_default_stack(self, client):
        response = client.post(
            "/aidan/build-prompt",
            json={"idea": "Job board", "core_feature": "Post and browse jobs"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "cursor_prompt" in data


# ---------------------------------------------------------------------------
# Weekly Review
# ---------------------------------------------------------------------------

class TestAidanWeeklyReview:
    def test_weekly_review_structure(self, client):
        response = client.post(
            "/aidan/weekly-review",
            json={
                "week_number": 3,
                "mrr": 150.0,
                "users": 22,
                "what_happened": "Got first 3 paying subscribers",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["week"] == 3
        assert data["mrr"] == 150.0
        assert data["mrr_gap"] == pytest.approx(350.0)
        assert "review" in data

    def test_weekly_review_zero_mrr(self, client):
        response = client.post(
            "/aidan/weekly-review",
            json={"week_number": 1, "mrr": 0.0, "users": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mrr_gap"] == 500.0

    def test_weekly_review_at_target(self, client):
        response = client.post(
            "/aidan/weekly-review",
            json={"week_number": 10, "mrr": 550.0, "users": 60},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["mrr_gap"] == 0.0


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_auth_disabled_allows_requests(self, client, monkeypatch):
        monkeypatch.setenv("ENABLE_AUTH", "false")
        response = client.post("/aidan/chat", json={"message": "test"})
        assert response.status_code == 200

    def test_auth_enabled_rejects_missing_key(self, monkeypatch):
        monkeypatch.setenv("ENABLE_AUTH", "true")
        monkeypatch.setenv("FRAMEWORK_API_KEY", "test-secret")
        from fastapi.testclient import TestClient
        from api.server import app
        c = TestClient(app)
        response = c.post("/aidan/chat", json={"message": "test"})
        assert response.status_code == 403

    def test_auth_enabled_accepts_correct_key(self, monkeypatch):
        monkeypatch.setenv("ENABLE_AUTH", "true")
        monkeypatch.setenv("FRAMEWORK_API_KEY", "test-secret")
        from fastapi.testclient import TestClient
        from api.server import app
        c = TestClient(app)
        response = c.post(
            "/aidan/chat",
            json={"message": "test"},
            headers={"X-API-Key": "test-secret"},
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
