"""
core/account_manager.py - Multi-account configurations and token budget tracking.
"""

from __future__ import annotations

import os
import json
import threading
import time
from typing import Any

from agent_workspace.core.security import validate_session_id


class QuotaExhaustedError(Exception):
    """Raised when all available LLM accounts are in cooldown or over token budget."""
    pass


class QuotaAwareRouter:
    """Manages 429 exponential backoff, RPM/TPM sliding windows, and account rotation."""

    def __init__(self, account_manager: AccountManager, base_cooldown: float = 5.0, max_cooldown: float = 120.0):
        self.account_manager = account_manager
        self.base_cooldown = base_cooldown
        self.max_cooldown = max_cooldown
        self._cooling_accounts: dict[str, float] = {}
        self._consecutive_429: dict[str, int] = {}
        self._telemetry_requests: dict[str, list[float]] = {}
        self._telemetry_tokens: dict[str, list[tuple[float, int]]] = {}
        self._lock = threading.Lock()

    def mark_rate_limited(self, account_id: str, retry_after: float | None = None) -> float:
        """Mark an account as rate-limited with exponential backoff or explicit retry_after."""
        with self._lock:
            count = self._consecutive_429.get(account_id, 0) + 1
            self._consecutive_429[account_id] = count
            if retry_after is not None:
                cd = float(retry_after)
            else:
                cd = min(self.base_cooldown * (2.0 ** (count - 1)), self.max_cooldown)
            self._cooling_accounts[account_id] = time.time() + cd
            return cd

    def is_account_cooling(self, account_id: str) -> bool:
        """Check if an account is currently cooling down. Auto-evicts expired accounts."""
        with self._lock:
            cooling_until = self._cooling_accounts.get(account_id)
            if cooling_until is None:
                return False
            if time.time() >= cooling_until:
                del self._cooling_accounts[account_id]
                return False
            return True

    def record_request_telemetry(self, account_id: str, tokens: int = 0) -> None:
        """Record a request timestamp and token count for RPM/TPM tracking."""
        with self._lock:
            now = time.time()
            self._telemetry_requests.setdefault(account_id, []).append(now)
            self._telemetry_tokens.setdefault(account_id, []).append((now, tokens))

    def get_rate_metrics(self, account_id: str, window_seconds: float = 60.0) -> tuple[int, int]:
        """Compute RPM and TPM for the given account over a sliding window."""
        with self._lock:
            now = time.time()
            cutoff = now - window_seconds
            reqs = [t for t in self._telemetry_requests.get(account_id, []) if t >= cutoff]
            self._telemetry_requests[account_id] = reqs
            toks = [(t, cnt) for (t, cnt) in self._telemetry_tokens.get(account_id, []) if t >= cutoff]
            self._telemetry_tokens[account_id] = toks
            rpm = len(reqs)
            tpm = sum(cnt for (_, cnt) in toks)
            return rpm, tpm

    def get_available_account(self, preferred_provider: str | None = None) -> dict[str, Any]:
        """Select a healthy account that is neither cooling nor budget-exhausted.

        Raises:
            QuotaExhaustedError: if no configured account is currently eligible.
        """
        accounts = self.account_manager.list_accounts()
        candidates: list[dict[str, Any]] = []

        for acc in accounts:
            acc_id = acc.get("id")
            if not acc_id:
                continue
            if self.is_account_cooling(acc_id):
                continue
            budget = acc.get("token_budget", -1)
            used = acc.get("tokens_used", 0)
            if budget != -1 and used >= budget:
                continue
            candidates.append(acc)

        if not candidates:
            raise QuotaExhaustedError("All available accounts are cooling or over budget.")

        if preferred_provider:
            pref_candidates = [
                acc for acc in candidates
                if acc.get("provider", "").lower() == preferred_provider.lower()
            ]
            if pref_candidates:
                for cand in pref_candidates:
                    if cand.get("is_active"):
                        return cand
                return pref_candidates[0]

        for cand in candidates:
            if cand.get("is_active"):
                return cand
        return candidates[0]

    def get_fallback_account_or_provider(
        self,
        failed_account_id: str | None = None,
        failed_provider: str | None = None,
        fallback_providers: tuple[str, ...] = ("google-genai", "ollama", "openai", "anthropic"),
    ) -> tuple[dict[str, Any] | None, str, str]:
        """
        Dynamically finds an eligible fallback account or provider when the current one is rate-limited.
        Returns (account_dict_or_none, provider_name, model_name).
        """
        accounts = self.account_manager.list_accounts()
        candidates: list[dict[str, Any]] = []

        for acc in accounts:
            acc_id = acc.get("id")
            if not acc_id or acc_id == failed_account_id:
                continue
            if self.is_account_cooling(acc_id):
                continue
            budget = acc.get("token_budget", -1)
            used = acc.get("tokens_used", 0)
            if budget != -1 and used >= budget:
                continue
            candidates.append(acc)

        # 1. Prefer candidate from alternate provider if failed_provider given
        if candidates and failed_provider:
            alt_candidates = [
                c for c in candidates
                if c.get("provider", "").lower() != failed_provider.lower()
            ]
            if alt_candidates:
                chosen = alt_candidates[0]
                return chosen, chosen.get("provider", "google-genai"), chosen.get("model", "gemini-1.5-flash")

        # 2. Candidate from same pool
        if candidates:
            chosen = candidates[0]
            return chosen, chosen.get("provider", "google-genai"), chosen.get("model", "gemini-1.5-flash")

        # 3. No candidate in configured accounts, fallback to default provider hierarchy
        failed_prov_norm = (failed_provider or "").lower()
        for prov in fallback_providers:
            if prov.lower() != failed_prov_norm:
                model = "gemini-1.5-flash" if "genai" in prov or "gemini" in prov else ("llama3" if prov == "ollama" else "gpt-4o-mini")
                return None, prov, model

        return None, "google-genai", "gemini-1.5-flash"


class AccountManager:
    """Manages secure loading, saving, and token usage tracking for multiple LLM accounts."""

    _session_tenants: dict[str, str] = {}
    _failovers: dict[str, dict[str, Any]] = {}

    @classmethod
    def register_session_tenant(cls, session_id: str, tenant_id: str) -> None:
        session_id = validate_session_id(session_id)
        cls._session_tenants[session_id] = tenant_id

    @classmethod
    def get_session_tenant(cls, session_id: str) -> str | None:
        session_id = validate_session_id(session_id)
        return cls._session_tenants.get(session_id)

    @classmethod
    def register_failover(cls, original_account_id: str, fallback_account_id: str, markup_multiplier: float = 1.8) -> None:
        cls._failovers[original_account_id] = {
            "fallback_account_id": fallback_account_id,
            "markup_multiplier": markup_multiplier
        }

    @classmethod
    def get_failover(cls, original_account_id: str) -> dict[str, Any] | None:
        return cls._failovers.get(original_account_id)

    @classmethod
    def clear_failovers(cls) -> None:
        cls._failovers.clear()

    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.accounts_path = os.path.join(self.workspace_path, "accounts.json")
        self.config_path = os.path.join(self.workspace_path, "config.yaml")
        self._lock = threading.Lock()
        self.quota_router = QuotaAwareRouter(self)
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

    def record_usage(
        self,
        account_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        session_id: str = "default-session",
        usage_id: str | None = None,
    ) -> bool:
        # Check failover mapping
        failover_info = self.get_failover(account_id)
        target_account_id = failover_info["fallback_account_id"] if failover_info else account_id
        markup = failover_info["markup_multiplier"] if failover_info else None
        from agent_workspace.core.ledger import FinancialLedger

        tenant_id = self.get_session_tenant(session_id) or "default_tenant"
        ledger = FinancialLedger(self.workspace_path)
        if usage_id and ledger.has_idempotency_key(tenant_id, usage_id):
            return True

        data = self._load_data()
        accounts = data.get("accounts", [])
        updated = False
        provider = "google-genai"
        model = "gemini-2.5-flash"
        
        for acc in accounts:
            if acc["id"] == target_account_id:
                acc["tokens_used"] = acc.get("tokens_used", 0) + prompt_tokens + completion_tokens
                provider = acc.get("provider", provider)
                model = acc.get("model", model)
                updated = True
                break
                
        if updated:
            self._save_accounts(data)
            ledger.record_transaction(
                session_id=session_id,
                account_id=target_account_id,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                tenant_id=tenant_id,
                markup_multiplier=markup,
                idempotency_key=usage_id,
            )
            
            # Check budget and rotate/downscale if threshold exceeded
            self.check_and_rotate_budget(target_account_id, session_id)
            
        return updated

    def resolve_api_key(self, account: dict[str, Any]) -> str:
        api_key = account.get("api_key", "")
        if isinstance(api_key, str) and api_key.startswith("env:"):
            env_var_name = api_key.split("env:", 1)[1].strip()
            return os.environ.get(env_var_name, "")
        return api_key

    def get_optimal_account_for_task(self, task_type: str) -> dict[str, Any] | None:
        """
        Query the global CloudCostRouter to select the best account among available configured accounts.
        """
        accounts = self.list_accounts()
        if not accounts:
            return self.get_active_account()

        providers_map = {}
        for acc in accounts:
            prov = acc.get("provider", "").lower()
            if prov:
                providers_map[prov] = acc

        if not providers_map:
            return self.get_active_account()

        from agent_workspace.observability import get_cost_router

        router = get_cost_router()
        optimal_provider = router.select_optimal_provider(task_type, list(providers_map.keys()))
        
        return providers_map.get(optimal_provider.lower(), self.get_active_account())

