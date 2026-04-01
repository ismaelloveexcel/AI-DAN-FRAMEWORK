"""
Tests for agent lazy initialization and async improvements.

Validates that:
- Agents are not created at import time (lazy initialization)
- The _agents cache stores instances after first access
- The _is_mock_mode property on BaseAgent delegates to core.config.is_mock_mode
- Async endpoints offload synchronous work to threads
"""

import os
import asyncio
import pytest
from unittest.mock import patch, MagicMock

# Ensure mock mode is enabled for all tests in this module
os.environ["USE_MOCK_KB"] = "true"


class TestLazyAgentInitialization:
    """Tests verifying that agents are created lazily (not at import time)."""

    def test_import_api_server_does_not_instantiate_agents(self):
        """Importing api_server must not create any agent instances."""
        import importlib
        import sys

        # Remove cached module so we can re-import cleanly
        for mod in list(sys.modules.keys()):
            if "api_server" in mod:
                del sys.modules[mod]

        # Track BaseAgent.__init__ calls
        call_count = 0

        import core.agent as agent_module
        original_init = agent_module.BaseAgent.__init__

        def counting_init(self, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_init(self, *args, **kwargs)

        with patch.object(agent_module.BaseAgent, "__init__", counting_init):
            import api_server  # noqa: F401

        assert call_count == 0, (
            f"Expected 0 BaseAgent.__init__ calls during import, got {call_count}"
        )

    def test_lazy_factory_returns_same_instance(self):
        """Calling a lazy factory twice must return the same cached instance."""
        import api_server

        # Reset cache to ensure clean state
        api_server._agents.clear()

        agent_a = api_server._get_research_agent()
        agent_b = api_server._get_research_agent()

        assert agent_a is agent_b, "Lazy factory must return the same cached instance"

    def test_lazy_factory_populates_cache(self):
        """After first access the agent must be stored in _agents."""
        import api_server

        api_server._agents.clear()

        assert "research" not in api_server._agents
        api_server._get_research_agent()
        assert "research" in api_server._agents

    def test_separate_agents_cached_independently(self):
        """Research and writer agents are cached under different keys."""
        import api_server

        api_server._agents.clear()

        ra = api_server._get_research_agent()
        wa = api_server._get_writer_agent()

        assert ra is not wa
        assert "research" in api_server._agents
        assert "writer" in api_server._agents


class TestMockModeProperty:
    """Tests for BaseAgent._is_mock_mode centralized config usage."""

    def test_is_mock_mode_true_when_env_set(self):
        """_is_mock_mode returns True when USE_MOCK_KB=true."""
        from core.config import reload_settings
        from agents.examples import ResearchAgent

        os.environ["USE_MOCK_KB"] = "true"
        reload_settings()

        agent = ResearchAgent()
        assert agent._is_mock_mode is True

    def test_is_mock_mode_false_when_env_unset(self):
        """_is_mock_mode returns False when USE_MOCK_KB=false."""
        from core.config import reload_settings
        from agents.examples import ResearchAgent

        os.environ["USE_MOCK_KB"] = "false"
        reload_settings()

        agent = ResearchAgent()
        assert agent._is_mock_mode is False

        # Restore
        os.environ["USE_MOCK_KB"] = "true"
        reload_settings()

    def test_agent_uses_mock_mode_for_task_execution(self):
        """Agent executes tasks via mock path when USE_MOCK_KB=true."""
        from core.config import reload_settings
        from agents.examples import ResearchAgent

        os.environ["USE_MOCK_KB"] = "true"
        reload_settings()

        agent = ResearchAgent()
        result = agent.research_topic(topic="AI testing", depth="basic")

        assert result["status"] == "completed"
        assert result["topic"] == "AI testing"
        assert result["findings"]  # Some mock result must be returned


class TestAsyncEndpoints:
    """Tests for async behaviour of API endpoints."""

    @pytest.fixture
    def test_client(self):
        from fastapi.testclient import TestClient
        from api_server import app
        return TestClient(app)

    def test_research_endpoint_async(self, test_client):
        """The /research endpoint returns a valid response."""
        response = test_client.post(
            "/research",
            json={"topic": "async programming", "depth": "basic"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "research_agent"
        assert data["status"] == "completed"

    def test_write_endpoint_async(self, test_client):
        """The /write endpoint returns a valid response."""
        response = test_client.post(
            "/write",
            json={"topic": "Python best practices", "tone": "professional", "word_count": 200},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent"] == "writer_agent"
        assert data["status"] == "completed"

    def test_collaborate_endpoint_runs_both_agents(self, test_client):
        """The /collaborate endpoint invokes both research and writer agents."""
        response = test_client.post(
            "/collaborate",
            json={"topic": "machine learning", "output_type": "blog_post"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "research_phase" in data
        assert "writing_phase" in data
        assert set(data["agents_involved"]) == {"research_agent", "writer_agent"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
