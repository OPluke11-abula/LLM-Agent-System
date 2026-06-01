"""
core/account_manager.py - Multi-account configurations and token budget tracking.
"""

from __future__ import annotations

import os
import json
import threading
from typing import Any


class AccountManager:
    """Manages secure loading, saving, and token usage tracking for multiple LLM accounts."""

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.accounts_path = os.path.join(self.workspace_path, "accounts.json")
        self.config_path = os.path.join(self.workspace_path, "config.yaml")
        self._lock = threading.Lock()
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not os.path.exists(self.accounts_path):
            provider = "google-genai"
            model = "gemini-2.5-flash"
            if os.path.exists(self.config_path):
                try:
                    import yaml
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}
                        llm = config.get("llm", {})
                        provider = llm.get("provider", provider)
                        model = llm.get("model", model)
                except Exception:
                    pass

            env_key_map = {
                "google-genai": "GOOGLE_API_KEY",
                "gemini": "GOOGLE_API_KEY",
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY"
            }
            api_key_env = env_key_map.get(provider.lower(), "")

            default_account = {
                "id": "default-account",
                "provider": provider,
                "model": model,
                "api_key": f"env:{api_key_env}" if api_key_env else "",
                "base_url": "",
                "token_budget": -1,
                "tokens_used": 0,
                "is_active": True
            }

            self._save_accounts({"accounts": [default_account], "active_account_id": "default-account"})

    def _load_data(self) -> dict[str, Any]:
        with self._lock:
            try:
                if os.path.exists(self.accounts_path):
                    with open(self.accounts_path, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {"accounts": [], "active_account_id": ""}

    def _save_accounts(self, data: dict[str, Any]) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.accounts_path), exist_ok=True)
            with open(self.accounts_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def list_accounts(self) -> list[dict[str, Any]]:
        return self._load_data().get("accounts", [])

    def add_account(self, account: dict[str, Any]) -> None:
        data = self._load_data()
        accounts = data.get("accounts", [])

        # Setup standard fields
        account.setdefault("base_url", "")
        account.setdefault("token_budget", -1)
        account.setdefault("tokens_used", 0)
        account.setdefault("is_active", False)

        # Check duplicate
        for i, acc in enumerate(accounts):
            if acc["id"] == account["id"]:
                accounts[i] = account
                break
        else:
            accounts.append(account)

        data["accounts"] = accounts
        if not data.get("active_account_id") or account.get("is_active"):
            data["active_account_id"] = account["id"]

        self._save_accounts(data)

    def get_account(self, account_id: str) -> dict[str, Any] | None:
        for acc in self.list_accounts():
            if acc["id"] == account_id:
                return acc
        return None

    def delete_account(self, account_id: str) -> bool:
        data = self._load_data()
        accounts = data.get("accounts", [])
        initial_len = len(accounts)
        accounts = [acc for acc in accounts if acc["id"] != account_id]
        if len(accounts) == initial_len:
            return False

        data["accounts"] = accounts
        if data.get("active_account_id") == account_id:
            data["active_account_id"] = accounts[0]["id"] if accounts else ""

        self._save_accounts(data)
        return True

    def get_active_account(self) -> dict[str, Any] | None:
        data = self._load_data()
        active_id = data.get("active_account_id", "")
        accounts = data.get("accounts", [])

        for acc in accounts:
            if acc["id"] == active_id:
                return acc
        for acc in accounts:
            if acc.get("is_active"):
                return acc
        if accounts:
            return accounts[0]
        return None

    def set_active_account(self, account_id: str) -> bool:
        data = self._load_data()
        accounts = data.get("accounts", [])
        found = False
        for acc in accounts:
            if acc["id"] == account_id:
                acc["is_active"] = True
                data["active_account_id"] = account_id
                found = True
            else:
                acc["is_active"] = False

        if found:
            self._save_accounts(data)
        return found

    def swap_to_fallback(self) -> bool:
        """Finds a fallback account and sets it active. Returns True if swapped, False otherwise."""
        data = self._load_data()
        active_id = data.get("active_account_id", "")
        accounts = data.get("accounts", [])
        
        for acc in accounts:
            if acc["id"] != active_id:
                budget = acc.get("token_budget", -1)
                used = acc.get("tokens_used", 0)
                if budget == -1 or used < budget:
                    data["active_account_id"] = acc["id"]
                    for a in accounts:
                        a["is_active"] = (a["id"] == acc["id"])
                    self._save_accounts(data)
                    return True
        return False

    def check_and_rotate_budget(self, account_id: str, session_id: str = "default-session") -> None:
        """Checks if accumulated ledger expenses exceed the cost threshold and rotates credentials/models."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from core.ledger import FinancialLedger
        except ImportError:
            from agent_workspace.core.ledger import FinancialLedger
            
        ledger = FinancialLedger(self.workspace_path)
        total_cost = ledger.get_total_cost()
        
        # Read cost threshold from config.yaml, default to 0.05 USD
        cost_threshold = 0.05
        if os.path.exists(self.config_path):
            try:
                import yaml
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                    cost_threshold = config.get("billing", {}).get("cost_threshold", 0.05)
            except Exception:
                pass
                
        if total_cost >= cost_threshold:
            logger.warning(
                "[CFO Cost Alert] Total swarm expenses of $%0.6f exceed threshold of $%0.6f. Triggering dynamic billing quota failover rotator...",
                total_cost, cost_threshold
            )
            
            data = self._load_data()
            accounts = data.get("accounts", [])
            active_id = data.get("active_account_id", "")
            
            rotated = False
            for acc in accounts:
                if acc["id"] == active_id:
                    model = acc.get("model", "")
                    if "pro" in model.lower():
                        cheaper = model.replace("pro", "flash")
                        logger.info("[CFO Rotator] Graceful Downscaling: downgrading model from %s to %s", model, cheaper)
                        acc["model"] = cheaper
                        rotated = True
                        break
            
            if not rotated:
                # Quota failover credential rotation:
                # Find the next available account in accounts.json that is under budget
                for acc in accounts:
                    if acc["id"] != active_id:
                        acc_budget = acc.get("token_budget", -1)
                        acc_used = acc.get("tokens_used", 0)
                        if acc_budget == -1 or acc_used < acc_budget:
                            logger.info("[CFO Rotator] Credential Rotation: rotating active account to fallback '%s'", acc["id"])
                            data["active_account_id"] = acc["id"]
                            for a in accounts:
                                a["is_active"] = (a["id"] == acc["id"])
                            rotated = True
                            break
                            
            if rotated:
                self._save_accounts(data)

    def record_usage(self, account_id: str, prompt_tokens: int, completion_tokens: int, session_id: str = "default-session") -> bool:
        data = self._load_data()
        accounts = data.get("accounts", [])
        updated = False
        provider = "google-genai"
        model = "gemini-2.5-flash"
        
        for acc in accounts:
            if acc["id"] == account_id:
                acc["tokens_used"] = acc.get("tokens_used", 0) + prompt_tokens + completion_tokens
                provider = acc.get("provider", provider)
                model = acc.get("model", model)
                updated = True
                break
                
        if updated:
            self._save_accounts(data)
            
            # Record in SQLite financial ledger
            try:
                from core.ledger import FinancialLedger
            except ImportError:
                from agent_workspace.core.ledger import FinancialLedger
                
            ledger = FinancialLedger(self.workspace_path)
            ledger.record_transaction(
                session_id=session_id,
                account_id=account_id,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            
            # Check budget and rotate/downscale if threshold exceeded
            self.check_and_rotate_budget(account_id, session_id)
            
        return updated

    def resolve_api_key(self, account: dict[str, Any]) -> str:
        api_key = account.get("api_key", "")
        if isinstance(api_key, str) and api_key.startswith("env:"):
            env_var_name = api_key.split("env:", 1)[1].strip()
            return os.environ.get(env_var_name, "")
        return api_key
