"""
Tests for n8n Bidirectional Integration

This module tests both directions of n8n integration:
1. n8n → Framework: n8n workflows calling framework API endpoints
2. Framework → n8n: Framework agents triggering n8n workflows via MCP
"""

import pytest
import os
import json
import importlib
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from core.config import reload_settings

# Set mock mode for testing
os.environ['USE_MOCK_KB'] = 'true'


@pytest.fixture
def api_app():
    """Reload api_server module so env-driven settings are re-evaluated."""
    os.environ.setdefault("ENABLE_AUTH", "false")
    os.environ.setdefault("FRAMEWORK_API_KEY", "default-test-key")
    os.environ.setdefault("API__ENABLE_AUTH", "false")
    os.environ.setdefault("API__API_KEY", "default-test-key")
    import api_server
    return importlib.reload(api_server).app


class TestN8NWebhookEndpoints:
    """Tests for n8n → Framework integration (Direction 1)"""

    @pytest.fixture
    def test_client(self, api_app):
        """Create a test client for the FastAPI app"""
        from fastapi.testclient import TestClient
        return TestClient(api_app)

    @pytest.fixture(autouse=True)
    def reset_auth_env(self):
        """Ensure auth env is deterministic across tests."""
        previous = {
            "ENABLE_AUTH": os.environ.get("ENABLE_AUTH"),
            "FRAMEWORK_API_KEY": os.environ.get("FRAMEWORK_API_KEY"),
            "API__ENABLE_AUTH": os.environ.get("API__ENABLE_AUTH"),
            "API__API_KEY": os.environ.get("API__API_KEY"),
        }

        os.environ["ENABLE_AUTH"] = "false"
        os.environ["FRAMEWORK_API_KEY"] = "default-test-key"
        os.environ["API__ENABLE_AUTH"] = "false"
        os.environ["API__API_KEY"] = "default-test-key"
        reload_settings()
        yield

        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reload_settings()

    @pytest.fixture
    def api_key_headers(self):
        """Headers with valid API key"""
        return {"X-API-Key": os.getenv("FRAMEWORK_API_KEY", "jts-dev-key-replace-in-production")}

    def test_n8n_webhook_sales_trigger(self, test_client, api_key_headers):
        """Test n8n webhook with sales trigger type"""
        payload = {
            "workflow_id": "test-workflow-123",
            "trigger_type": "sales",
            "payload": {
                "action": "qualify",
                "lead_id": "L001",
                "lead_name": "John Doe"
            }
        }

        response = test_client.post(
            "/n8n/webhook",
            json=payload,
            headers=api_key_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["workflow_id"] == "test-workflow-123"
        assert data["trigger_type"] == "sales"

    def test_n8n_webhook_marketing_trigger(self, test_client, api_key_headers):
        """Test n8n webhook with marketing trigger type"""
        payload = {
            "workflow_id": "test-workflow-456",
            "trigger_type": "marketing",
            "payload": {
                "action": "generate_content",
                "topic": "AI Automation"
            }
        }

        response = test_client.post(
            "/n8n/webhook",
            json=payload,
            headers=api_key_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["trigger_type"] == "marketing"

    def test_n8n_webhook_research_trigger(self, test_client, api_key_headers):
        """Test n8n webhook with research trigger type"""
        payload = {
            "workflow_id": "test-workflow-789",
            "trigger_type": "research",
            "payload": {
                "topic": "Market Trends 2025",
                "depth": "comprehensive"
            }
        }

        response = test_client.post(
            "/n8n/webhook",
            json=payload,
            headers=api_key_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_n8n_webhook_requires_auth(self, test_client):
        """Test that webhook requires API key when auth is enabled"""
        previous_enable_auth = os.environ.get("ENABLE_AUTH")
        previous_api_key = os.environ.get("FRAMEWORK_API_KEY")
        previous_nested_auth = os.environ.get("API__ENABLE_AUTH")
        previous_nested_api_key = os.environ.get("API__API_KEY")
        os.environ["ENABLE_AUTH"] = "true"
        os.environ["FRAMEWORK_API_KEY"] = "auth-test-key"
        os.environ["API__ENABLE_AUTH"] = "true"
        os.environ["API__API_KEY"] = "auth-test-key"
        reload_settings()
        payload = {
            "workflow_id": "test-workflow",
            "trigger_type": "sales",
            "payload": {}
        }

        response = test_client.post("/n8n/webhook", json=payload)
        assert response.status_code == 403

        if previous_enable_auth is None:
            del os.environ["ENABLE_AUTH"]
        else:
            os.environ["ENABLE_AUTH"] = previous_enable_auth
        if previous_api_key is None:
            del os.environ["FRAMEWORK_API_KEY"]
        else:
            os.environ["FRAMEWORK_API_KEY"] = previous_api_key
        if previous_nested_auth is None:
            del os.environ["API__ENABLE_AUTH"]
        else:
            os.environ["API__ENABLE_AUTH"] = previous_nested_auth
        if previous_nested_api_key is None:
            del os.environ["API__API_KEY"]
        else:
            os.environ["API__API_KEY"] = previous_nested_api_key
        reload_settings()

    def test_n8n_webhook_auth_disabled_allows_requests(self, test_client):
        """Test that webhook allows requests when auth is disabled."""
        previous_enable_auth = os.environ.get("ENABLE_AUTH")
        previous_api_key = os.environ.get("FRAMEWORK_API_KEY")
        previous_nested_auth = os.environ.get("API__ENABLE_AUTH")
        previous_nested_api_key = os.environ.get("API__API_KEY")
        os.environ["ENABLE_AUTH"] = "false"
        os.environ["FRAMEWORK_API_KEY"] = "auth-test-key"
        os.environ["API__ENABLE_AUTH"] = "false"
        os.environ["API__API_KEY"] = "auth-test-key"
        reload_settings()
        payload = {
            "workflow_id": "test-workflow",
            "trigger_type": "sales",
            "payload": {}
        }

        response = test_client.post("/n8n/webhook", json=payload)
        assert response.status_code == 200

        if previous_enable_auth is None:
            del os.environ["ENABLE_AUTH"]
        else:
            os.environ["ENABLE_AUTH"] = previous_enable_auth
        if previous_api_key is None:
            del os.environ["FRAMEWORK_API_KEY"]
        else:
            os.environ["FRAMEWORK_API_KEY"] = previous_api_key
        if previous_nested_auth is None:
            del os.environ["API__ENABLE_AUTH"]
        else:
            os.environ["API__ENABLE_AUTH"] = previous_nested_auth
        if previous_nested_api_key is None:
            del os.environ["API__API_KEY"]
        else:
            os.environ["API__API_KEY"] = previous_nested_api_key
        reload_settings()


class TestSalesEndpoints:
    """Tests for Sales API endpoints"""

    @pytest.fixture
    def test_client(self, api_app):
        from fastapi.testclient import TestClient
        return TestClient(api_app)

    @pytest.fixture
    def api_key_headers(self):
        return {"X-API-Key": os.getenv("FRAMEWORK_API_KEY", "jts-dev-key-replace-in-production")}

    def test_process_lead(self, test_client, api_key_headers):
        """Test lead processing endpoint"""
        payload = {
            "lead_name": "Jane Smith",
            "lead_email": "jane@example.com",
            "lead_company": "Tech Corp",
            "lead_source": "n8n_webhook"
        }

        response = test_client.post(
            "/sales/process-lead",
            json=payload,
            headers=api_key_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "lead" in data
        assert data["lead"]["name"] == "Jane Smith"

    def test_qualify_lead(self, test_client, api_key_headers):
        """Test lead qualification endpoint"""
        payload = {
            "lead_id": "L001",
            "lead_data": {
                "company": "Enterprise Inc",
                "company_size": 250,
                "industry": "technology"
            },
            "icp_criteria": {
                "company_size": "100-500 employees",
                "industries": ["technology", "finance"]
            }
        }

        response = test_client.post(
            "/sales/qualify-lead",
            json=payload,
            headers=api_key_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["lead_id"] == "L001"


class TestMarketingEndpoints:
    """Tests for Marketing API endpoints"""

    @pytest.fixture
    def test_client(self, api_app):
        from fastapi.testclient import TestClient
        return TestClient(api_app)

    @pytest.fixture
    def api_key_headers(self):
        return {"X-API-Key": os.getenv("FRAMEWORK_API_KEY", "jts-dev-key-replace-in-production")}

    def test_generate_content(self, test_client, api_key_headers):
        """Test content generation endpoint"""
        payload = {
            "action": "generate_content",
            "campaign_name": "Q1 Campaign",
            "parameters": {
                "content_type": "blog_post",
                "topic": "AI in Business",
                "tone": "professional",
                "word_count": 800
            }
        }

        response = test_client.post(
            "/marketing/generate-content",
            json=payload,
            headers=api_key_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["content_type"] == "blog_post"

    def test_analyze_campaign(self, test_client, api_key_headers):
        """Test campaign analysis endpoint"""
        payload = {
            "action": "analyze",
            "campaign_name": "Spring Launch",
            "parameters": {
                "campaign_data": {
                    "impressions": 50000,
                    "clicks": 2500,
                    "conversions": 125,
                    "spend": 5000
                }
            }
        }

        response = test_client.post(
            "/marketing/analyze-campaign",
            json=payload,
            headers=api_key_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["campaign_name"] == "Spring Launch"


class TestN8NMCPTools:
    """Tests for Framework → n8n integration (Direction 2)"""

    def test_n8n_trigger_workflow_tool_initialization(self):
        """Test N8NTriggerWorkflowTool initializes correctly"""
        from core.tools import N8NTriggerWorkflowTool

        tool = N8NTriggerWorkflowTool()
        assert tool.name == "n8n Trigger Workflow Tool"
        assert "workflow" in tool.description.lower()

    def test_n8n_execute_workflow_tool_initialization(self):
        """Test N8NExecuteWorkflowTool has distinct name contract"""
        from core.tools import N8NExecuteWorkflowTool

        tool = N8NExecuteWorkflowTool()
        assert tool.name == "n8n Execute Workflow Tool"
        assert "workflow" in tool.description.lower()

    def test_n8n_execute_workflow_tool_initialization(self):
        """Test N8NExecuteWorkflowTool has unique stable name."""
        from core.tools import N8NExecuteWorkflowTool

        tool = N8NExecuteWorkflowTool()
        assert tool.name == "n8n Execute Workflow Tool"

    def test_n8n_list_workflows_tool_initialization(self):
        """Test N8NListWorkflowsTool initializes correctly"""
        from core.tools import N8NListWorkflowsTool

        tool = N8NListWorkflowsTool()
        assert tool.name == "n8n List Workflows Tool"

    def test_n8n_sales_automation_tool_initialization(self):
        """Test N8NSalesAutomationTool initializes correctly"""
        from core.tools import N8NSalesAutomationTool

        tool = N8NSalesAutomationTool()
        assert tool.name == "n8n Sales Automation Tool"
        assert "nurture_lead" in str(tool.description) or hasattr(tool, 'workflow_map')

    def test_n8n_marketing_automation_tool_initialization(self):
        """Test N8NMarketingAutomationTool initializes correctly"""
        from core.tools import N8NMarketingAutomationTool

        tool = N8NMarketingAutomationTool()
        assert tool.name == "n8n Marketing Automation Tool"

    @patch('requests.post')
    def test_n8n_trigger_workflow_call(self, mock_post):
        """Test that trigger workflow tool makes correct HTTP call"""
        from core.tools import N8NTriggerWorkflowTool

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<tool_output>Success</tool_output>'
        mock_post.return_value = mock_response

        tool = N8NTriggerWorkflowTool()
        result = tool._run(workflow_id="test-123", input_data={"key": "value"})

        # Verify the call was made
        assert mock_post.called

    def test_sales_automation_unknown_action(self):
        """Test sales automation tool handles unknown actions"""
        from core.tools import N8NSalesAutomationTool

        tool = N8NSalesAutomationTool()
        result = tool._run(action="unknown_action", lead_data={})

        assert "Unknown" in result or "unconfigured" in result


class TestSalesAgents:
    """Tests for Sales department agents"""

    def test_sales_lead_agent_initialization(self):
        """Test SalesLeadAgent initializes correctly"""
        from agents.sales import SalesLeadAgent

        agent = SalesLeadAgent()
        assert agent.config.id == "sales_lead_agent"
        assert agent.config.department == "sales"

    def test_outreach_agent_initialization(self):
        """Test OutreachAgent initializes correctly"""
        from agents.sales import OutreachAgent

        agent = OutreachAgent()
        assert agent.config.id == "outreach_agent"
        assert agent.config.department == "sales"


class TestMarketingAgents:
    """Tests for Marketing department agents"""

    def test_content_marketing_agent_initialization(self):
        """Test ContentMarketingAgent initializes correctly"""
        from agents.marketing import ContentMarketingAgent

        agent = ContentMarketingAgent()
        assert agent.config.id == "content_marketing_agent"
        assert agent.config.department == "marketing"

    def test_campaign_agent_initialization(self):
        """Test CampaignAgent initializes correctly"""
        from agents.marketing import CampaignAgent

        agent = CampaignAgent()
        assert agent.config.id == "campaign_agent"
        assert agent.config.department == "marketing"


class TestToolFactory:
    """Tests for tool factory n8n tool registration"""

    def test_n8n_tools_registered_in_mock_mode(self):
        """Test n8n tools are available in mock mode"""
        os.environ['USE_MOCK_KB'] = 'true'
        from core.tools import get_tool_by_name

        tool_names = [
            "n8n_trigger_workflow_tool",
            "n8n_list_workflows_tool",
            "n8n_sales_automation_tool",
            "n8n_marketing_automation_tool",
            "n8n_execute_workflow_tool"
        ]

        for name in tool_names:
            tool = get_tool_by_name(name)
            assert tool is not None, f"Tool {name} should be registered"

    def test_create_mock_tool_dict_fallback(self):
        """Ensure mock fallback dictionary uses function arguments."""
        from core import tools as tools_module

        previous = tools_module.CREWAI_AVAILABLE
        tools_module.CREWAI_AVAILABLE = False
        try:
            tool = tools_module.create_mock_tool("sample tool", "sample description")
            assert isinstance(tool, dict)
            assert tool["name"] == "sample tool"
            assert tool["description"] == "sample description"
        finally:
            tools_module.CREWAI_AVAILABLE = previous


class TestAPIConfiguration:
    """Tests for API config-driven auth and CORS behavior."""

    @pytest.fixture
    def test_client(self, api_app):
        from fastapi.testclient import TestClient
        return TestClient(api_app)

    def test_cors_preflight_reflects_origin(self, test_client):
        """When CORS is configured, preflight should return origin header."""
        previous = os.environ.get("CORS_ORIGINS")
        previous_nested = os.environ.get("API__CORS_ORIGINS")
        os.environ["CORS_ORIGINS"] = "http://localhost:3000"
        os.environ["API__CORS_ORIGINS"] = "http://localhost:3000"
        reload_settings()
        import importlib
        import api_server
        from fastapi.testclient import TestClient
        dynamic_client = TestClient(importlib.reload(api_server).app)

        response = dynamic_client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in (200, 204)
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

        if previous is None:
            del os.environ["CORS_ORIGINS"]
        else:
            os.environ["CORS_ORIGINS"] = previous
        if previous_nested is None:
            del os.environ["API__CORS_ORIGINS"]
        else:
            os.environ["API__CORS_ORIGINS"] = previous_nested
        reload_settings()


class TestBidirectionalFlow:
    """Integration tests for complete bidirectional flow"""

    @pytest.fixture
    def test_client(self, api_app):
        from fastapi.testclient import TestClient
        return TestClient(api_app)

    @pytest.fixture
    def api_key_headers(self):
        return {"X-API-Key": os.getenv("FRAMEWORK_API_KEY", "jts-dev-key-replace-in-production")}

    def test_complete_sales_flow(self, test_client, api_key_headers):
        """Test complete sales flow: n8n -> Framework -> (would trigger n8n)"""
        # Step 1: n8n sends lead via webhook
        webhook_payload = {
            "workflow_id": "crm-new-lead",
            "trigger_type": "sales",
            "payload": {
                "action": "process",
                "lead_name": "Test Lead",
                "lead_email": "test@example.com",
                "lead_company": "Test Corp"
            }
        }

        response = test_client.post(
            "/n8n/webhook",
            json=webhook_payload,
            headers=api_key_headers
        )
        assert response.status_code == 200

        # Step 2: Process lead through dedicated endpoint
        lead_payload = {
            "lead_name": "Test Lead",
            "lead_email": "test@example.com",
            "lead_company": "Test Corp",
            "lead_source": "n8n_crm"
        }

        response = test_client.post(
            "/sales/process-lead",
            json=lead_payload,
            headers=api_key_headers
        )
        assert response.status_code == 200

        # Step 3: Qualify the lead
        qualify_payload = {
            "lead_id": "L-TEST-001",
            "lead_data": {
                "name": "Test Lead",
                "company": "Test Corp",
                "company_size": 150
            }
        }

        response = test_client.post(
            "/sales/qualify-lead",
            json=qualify_payload,
            headers=api_key_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
