import os
import sys
import json
import pytest
from fastapi.testclient import TestClient

# Ensure agent_workspace is in sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.builder import AgentBuilderRegistry, PRESET_TEMPLATES, render_system_prompt, emit_mock_webhook_telemetry
from core.ledger import FinancialLedger
from core.billing import SaaSBillingTracker
from api import app


@pytest.fixture(autouse=True)
def clean_registry_and_ledger():
    AgentBuilderRegistry.clear()
    ledger = FinancialLedger(workspace_dir)
    ledger.reset_ledger()
    yield
    AgentBuilderRegistry.clear()
    ledger.reset_ledger()


def test_jinja2_system_prompt_rendering():
    """Verify that render_system_prompt dynamically evaluates variables and loops."""
    template = (
        "Role: {{ role }}.\n"
        "Directives:\n"
        "{% for d in directives %}\n"
        "- {{ d }}\n"
        "{% endfor %}"
    )
    variables = {
        "role": "QA Architect",
        "directives": ["Analyze syntax", "Reject invalid types"]
    }
    rendered = render_system_prompt(template, variables)
    assert "Role: QA Architect." in rendered
    assert "- Analyze syntax" in rendered
    assert "- Reject invalid types" in rendered


def test_agent_builder_registry():
    """Verify AgentBuilderRegistry registration and querying capabilities."""
    config = {
        "role": "CFO",
        "description": "Ledger compliance officer",
        "guidelines": ["Check token budgets"],
        "system_template": "You are {{ name }}."
    }
    
    registered = AgentBuilderRegistry.register_agent("ledger_bot", config)
    assert registered["name"] == "ledger_bot"
    assert registered["role"] == "CFO"

    retrieved = AgentBuilderRegistry.get_agent("ledger_bot")
    assert retrieved is not None
    assert retrieved["description"] == "Ledger compliance officer"

    all_agents = AgentBuilderRegistry.get_all_agents()
    assert len(all_agents) == 1
    assert all_agents[0]["name"] == "ledger_bot"


def test_mock_webhook_telemetry():
    """Verify mock telemetry webhook logs formats for Slack and LINE configurations."""
    gateways = [
        {"type": "slack", "webhook_url": "https://hooks.slack.com/services/123"},
        {"type": "line", "webhook_url": "https://api.line.me/webhook/456"},
        {"type": "generic", "webhook_url": "https://example.com/webhook"}
    ]
    logs = emit_mock_webhook_telemetry(gateways, "Agent execution finished successfully")

    assert len(logs) == 3
    
    # Slack checks
    slack_log = [l for l in logs if l["gateway"] == "slack"][0]
    assert slack_log["payload_sent"]["text"] == "Agent execution finished successfully"
    assert slack_log["webhook_url"] == "https://hooks.slack.com/services/123"

    # LINE checks
    line_log = [l for l in logs if l["gateway"] == "line"][0]
    assert line_log["payload_sent"]["messages"][0]["text"] == "Agent execution finished successfully"
    
    # Generic checks
    generic_log = [l for l in logs if l["gateway"] == "generic"][0]
    assert generic_log["payload_sent"]["message"] == "Agent execution finished successfully"


def test_saas_billing_tracker_and_invoice():
    """Verify raw database calculations and SaaS Platform Invoice markup multiplier logic."""
    ledger = FinancialLedger(workspace_dir)
    
    # Record test transactions
    ledger.record_transaction("session-1", "user-A", "google", "gemini-1.5-pro", 100, 200)
    ledger.record_transaction("session-2", "user-A", "openai", "gpt-4o", 150, 250)
    ledger.record_transaction("session-1", "user-B", "google", "gemini-1.5-flash", 300, 400)

    tracker = SaaSBillingTracker(ledger)

    # 1. Total cost invoicing (no filter)
    invoice = tracker.get_saas_invoice(markup_multiplier=1.8)
    assert invoice["markup_multiplier"] == 1.8
    assert invoice["total_prompt_tokens"] == 100 + 150 + 300
    assert invoice["total_completion_tokens"] == 200 + 250 + 400
    assert invoice["raw_cost_usd"] > 0
    assert pytest.approx(invoice["billed_cost_usd"]) == invoice["raw_cost_usd"] * 1.8
    assert len(invoice["transactions"]) == 3
    assert "raw_cost" in invoice["transactions"][0]
    assert "billed_cost" in invoice["transactions"][0]

    # 2. Filtered invoicing (for session-1)
    invoice_filtered = tracker.get_saas_invoice(filter_id="session-1", markup_multiplier=1.5)
    assert invoice_filtered["total_prompt_tokens"] == 100 + 300
    assert invoice_filtered["total_completion_tokens"] == 200 + 400
    assert len(invoice_filtered["transactions"]) == 2


def test_builder_api_endpoints():
    """Verify create, template fetching, console testing, and invoice routes via FastAPI Client."""
    client = TestClient(app)

    # 1. Create Agent Persona via API
    payload = {
        "name": "strategy_coach",
        "role": "CEO Executive Coach",
        "description": "Guides strategy decisions",
        "guidelines": ["Keep strategies actionable"],
        "system_template": "You are {{ name }}. Focus on {{ topic }}.",
        "telemetry_gateways": [{"type": "slack", "webhook_url": "http://slack"}]
    }
    resp = client.post("/v1/builder/agents", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["agent"]["name"] == "strategy_coach"

    # 2. Get available templates via API
    resp_templates = client.get("/v1/builder/templates")
    assert resp_templates.status_code == 200
    data_templates = resp_templates.json()
    assert "templates" in data_templates
    assert len(data_templates["templates"]) > 0

    # 3. Test Agent Console Execution via API
    test_payload = {
        "agent_config": {
            "name": "strategy_coach",
            "model": "gemini-1.5-pro",
            "system_template": "You are {{ name }}. Focus: {{ focus }}.",
            "telemetry_gateways": [{"type": "slack", "webhook_url": "http://slack"}]
        },
        "test_input": "Suggest a marketing plan",
        "session_id": "test-session-console",
        "variables": {"focus": "Growth Marketing"}
    }
    resp_test = client.post("/v1/builder/test", json=test_payload)
    assert resp_test.status_code == 200
    data_test = resp_test.json()
    assert data_test["status"] == "success"
    assert data_test["rendered_prompt"] == "You are strategy_coach. Focus: Growth Marketing."
    assert "Console Test Output" in data_test["output"]
    assert data_test["estimated_cost_usd"] > 0
    assert len(data_test["telemetry_logs"]) == 1

    # 4. Fetch platform invoicing billing summary
    resp_invoice = client.get("/v1/billing/saas/invoice?filter_id=test-session-console&markup_multiplier=2.0")
    assert resp_invoice.status_code == 200
    data_invoice = resp_invoice.json()
    assert data_invoice["filter_id"] == "test-session-console"
    assert data_invoice["markup_multiplier"] == 2.0
    assert data_invoice["raw_cost_usd"] > 0
    assert pytest.approx(data_invoice["billed_cost_usd"]) == data_invoice["raw_cost_usd"] * 2.0
