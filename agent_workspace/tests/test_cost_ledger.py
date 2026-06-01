import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.ledger import FinancialLedger
from core.account_manager import AccountManager
from api import app


@pytest.fixture
def mock_ledger_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create standard directories
        (temp_path / "memory").mkdir(parents=True, exist_ok=True)
        
        # Scaffold accounts.json
        accounts_data = {
            "accounts": [
                {
                    "id": "premium-account",
                    "provider": "google-genai",
                    "model": "gemini-2.5-pro",
                    "api_key": "env:GOOGLE_API_KEY",
                    "base_url": "",
                    "token_budget": -1,
                    "tokens_used": 0,
                    "is_active": True
                },
                {
                    "id": "cheapest-account",
                    "provider": "google-genai",
                    "model": "gemini-2.5-flash",
                    "api_key": "env:GOOGLE_API_KEY",
                    "base_url": "",
                    "token_budget": -1,
                    "tokens_used": 0,
                    "is_active": False
                }
            ],
            "active_account_id": "premium-account"
        }
        (temp_path / "accounts.json").write_text(json.dumps(accounts_data, indent=2), encoding="utf-8")
        
        # Scaffold config.yaml
        config_yaml = """
llm:
  provider: google-genai
  model: gemini-2.5-pro
billing:
  cost_threshold: 0.01
"""
        (temp_path / "config.yaml").write_text(config_yaml, encoding="utf-8")
        
        yield str(temp_path)


def test_financial_ledger_sqlite_operations(mock_ledger_env):
    ledger = FinancialLedger(mock_ledger_env)
    
    # 1. Initially total cost is 0
    assert ledger.get_total_cost() == 0.0
    
    # 2. Record dynamic transactions
    # Cost for gemini-2.5-pro (pro tier): prompt_t * 0.000015 + comp_t * 0.000045
    # 100 prompt, 50 completion -> 100 * 0.000015 + 50 * 0.000045 = 0.0015 + 0.00225 = 0.00375
    cost_pro = ledger.record_transaction("session-1", "premium-account", "google-genai", "gemini-2.5-pro", 100, 50)
    assert cost_pro == pytest.approx(0.00375)
    
    # Cost for gemini-2.5-flash (flash tier): prompt_t * 0.000000075 + comp_t * 0.00000030
    # 1000 prompt, 500 completion -> 1000 * 0.000000075 + 500 * 0.0000003 = 0.000075 + 0.000150 = 0.000225
    cost_flash = ledger.record_transaction("session-1", "cheapest-account", "google-genai", "gemini-2.5-flash", 1000, 500)
    assert cost_flash == pytest.approx(0.000225)
    
    # 3. Sum up total cost
    assert ledger.get_total_cost() == pytest.approx(0.00375 + 0.000225)
    
    # 4. Filter total cost by session or account
    assert ledger.get_total_cost("premium-account") == pytest.approx(0.00375)
    
    # 5. List records
    records = ledger.get_all_records()
    assert len(records) == 2
    assert records[0]["session_id"] == "session-1"
    assert records[0]["model"] == "gemini-2.5-pro"
    
    # 6. Reset database
    ledger.reset_ledger()
    assert ledger.get_total_cost() == 0.0
    assert len(ledger.get_all_records()) == 0


def test_billing_failover_rotator_downscaling_and_credential_rotation(mock_ledger_env):
    am = AccountManager(mock_ledger_env)
    
    # Assert active account has "gemini-2.5-pro"
    active = am.get_active_account()
    assert active["id"] == "premium-account"
    assert active["model"] == "gemini-2.5-pro"
    
    # 1. Trigger graceful downscaling by exceeding cost threshold ($0.01)
    # Estimate cost to hit threshold. 
    # Let's record token usage: 400 prompt, 200 completion on 'premium-account'
    # Cost = 400 * 0.000015 + 200 * 0.000045 = 0.0060 + 0.0090 = 0.0150 USD (> 0.01 threshold)
    am.record_usage("premium-account", 400, 200, "session-test")
    
    # Check that dynamic downscaling changed gemini-2.5-pro to gemini-2.5-flash
    active = am.get_active_account()
    assert active["id"] == "premium-account"
    assert active["model"] == "gemini-2.5-flash"
    
    # 2. Trigger credential rotation as a fallback if budget is still exceeded
    # We exceed budget limit by adding more expenses.
    # Total threshold limit is still exceeded because costs are accumulated.
    # If premium-account does not have a "pro" model anymore (it is now flash),
    # the second check_and_rotate_budget will fall back to rotating to fallback 'cheapest-account'.
    am.record_usage("premium-account", 400, 200, "session-test")
    
    active = am.get_active_account()
    assert active["id"] == "cheapest-account"
    assert active["is_active"] is True


def test_api_ledger_endpoints(mock_ledger_env):
    import api
    api.workspace = mock_ledger_env
    
    client = TestClient(app)
    session_id = "ledger-api-session"
    
    # Reset ledger first
    client.post(f"/v1/sessions/{session_id}/ledger/reset")
    
    # Record some transactions by recording usage via account manager
    am = api.get_account_manager()
    am.workspace_path = mock_ledger_env
    am.accounts_path = os.path.join(mock_ledger_env, "accounts.json")
    am.config_path = os.path.join(mock_ledger_env, "config.yaml")
    
    am.record_usage("cheapest-account", 200, 100, session_id)
    
    # Verify GET ledger metrics endpoint
    resp = client.get(f"/v1/sessions/{session_id}/ledger")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["total_cost"] > 0.0
    assert data["cost_threshold"] == 0.01
    assert "cheapest-account" in [tx["account_id"] for tx in data["transactions"]]
