import os
import sys
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock, patch

# Ensure agent_workspace is in path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, workspace_dir)

from core.account_manager import AccountManager
from core.engine import AgentEngine
from core.router import AgentRouter

def test_account_manager_lifecycle():
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Initialization and default account creation
        manager = AccountManager(temp_dir)
        accounts = manager.list_accounts()
        assert len(accounts) == 1
        assert accounts[0]["id"] == "default-account"
        assert accounts[0]["provider"] == "google-genai"
        assert accounts[0]["model"] == "gemini-2.5-flash"
        assert accounts[0]["is_active"] is True

        # 2. Add a new account
        new_account = {
            "id": "test-openai",
            "provider": "openai",
            "model": "gpt-4o",
            "api_key": "literal_key_123",
            "token_budget": 1000,
            "is_active": False
        }
        manager.add_account(new_account)
        accounts = manager.list_accounts()
        assert len(accounts) == 2
        
        acc = manager.get_account("test-openai")
        assert acc is not None
        assert acc["provider"] == "openai"
        assert acc["api_key"] == "literal_key_123"
        assert acc["token_budget"] == 1000
        assert acc["tokens_used"] == 0
        
        # 3. Setting active account
        assert manager.get_active_account()["id"] == "default-account"
        success = manager.set_active_account("test-openai")
        assert success is True
        assert manager.get_active_account()["id"] == "test-openai"
        
        # 4. Token usage tracking
        success = manager.record_usage("test-openai", 100, 200)
        assert success is True
        acc = manager.get_account("test-openai")
        assert acc["tokens_used"] == 300
        
        # 5. Resolve API keys (literal vs env)
        os.environ["TEST_ENV_KEY"] = "env_key_value_456"
        env_account = {
            "id": "test-env",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet",
            "api_key": "env:TEST_ENV_KEY"
        }
        manager.add_account(env_account)
        
        resolved_literal = manager.resolve_api_key(manager.get_account("test-openai"))
        assert resolved_literal == "literal_key_123"
        
        resolved_env = manager.resolve_api_key(manager.get_account("test-env"))
        assert resolved_env == "env_key_value_456"
        
        # 6. Delete account
        deleted = manager.delete_account("test-openai")
        assert deleted is True
        assert manager.get_account("test-openai") is None
        # Since active account was deleted, active should fallback
        assert manager.get_active_account()["id"] != "test-openai"


def test_router_account_budget_failover():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create config.yaml
        with open(os.path.join(temp_dir, "config.yaml"), "w", encoding="utf-8") as f:
            f.write("llm:\n  provider: google-genai\n  model: gemini-2.5-flash\n")

        # Create .agent/skills directory
        os.makedirs(os.path.join(temp_dir, ".agent", "skills"), exist_ok=True)

        engine = AgentEngine(workspace_path=temp_dir)
        router = AgentRouter(engine=engine, session_id="test-session")
        try:
            # Set up accounts in account manager
            # Account 1: test-acc-1, budget=100, used=100 (exceeded)
            acc1 = {
                "id": "test-acc-1",
                "provider": "google-genai",
                "model": "gemini-2.5-flash",
                "api_key": "key1",
                "token_budget": 100,
                "tokens_used": 100,
                "is_active": True
            }
            # Account 2: test-acc-2, budget=500, used=100 (valid)
            acc2 = {
                "id": "test-acc-2",
                "provider": "google-genai",
                "model": "gemini-2.5-flash",
                "api_key": "key2",
                "token_budget": 500,
                "tokens_used": 100,
                "is_active": False
            }
            router.account_manager.add_account(acc1)
            router.account_manager.add_account(acc2)
            # Delete default-account so it doesn't interfere with failover target tests
            router.account_manager.delete_account("default-account")
            router.account_manager.set_active_account("test-acc-1")
            
            # Resolve active account should trigger failover to test-acc-2
            resolved = router._resolve_account()
            assert resolved["id"] == "test-acc-2"
            
            # Now make test-acc-2 also exceeded
            router.account_manager.record_usage("test-acc-2", 200, 200) # total used = 500
            
            # Resolve account should raise RuntimeError since all fallback are exceeded
            with pytest.raises(RuntimeError) as excinfo:
                router._resolve_account()
            assert "Token budget exceeded" in str(excinfo.value)
        finally:
            router.close()
