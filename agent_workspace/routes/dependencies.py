import os
import sys
import base64
import json
import hmac
import hashlib
import time
import logging
import inspect
import secrets
import uuid
import math
import yaml
from pathlib import Path
from typing import Any
from fastapi import Header, HTTPException, WebSocket

from agent_workspace.core.engine import AgentEngine
from agent_workspace.core.router import AgentRouter
from agent_workspace.long_term_memory import LongTermMemoryStore
from agent_workspace.core.account_manager import AccountManager
from agent_workspace.core.billing import QuotaExceededError
from agent_workspace.core.security import validate_session_id


logger = logging.getLogger("api.dependencies")

# Since dependencies.py is in agent_workspace/routes/dependencies.py,
# os.path.dirname(os.path.dirname(os.path.abspath(__file__))) points to agent_workspace/
workspace = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_workspace() -> str:
    legacy_workspace = None
    try:
        import api
        if hasattr(api, "workspace") and api.workspace:
            legacy_workspace = api.workspace
    except Exception:
        pass

    # Preserve the legacy test/embedding seam: an explicit api.workspace
    # override must win over the process-level environment setting.
    if legacy_workspace and os.path.abspath(legacy_workspace) != os.path.abspath(workspace):
        return legacy_workspace

    env_dir = os.environ.get("AGENT_WORKSPACE_DIR")
    if env_dir:
        return env_dir
    if legacy_workspace:
        return legacy_workspace
    return workspace

_engine: AgentEngine | None = None

def get_engine() -> AgentEngine:
    global _engine
    legacy_api = sys.modules.get("api") or sys.modules.get("agent_workspace.api")
    legacy_engine = getattr(legacy_api, "_engine", None) if legacy_api else None
    if legacy_engine is not None and legacy_engine is not _engine:
        _engine = legacy_engine
    if _engine is None:
        _engine = AgentEngine(workspace_path=get_workspace())
    return _engine

def get_account_manager() -> AccountManager:
    return AccountManager(get_workspace())


def require_valid_session_id(session_id: str) -> str:
    try:
        return validate_session_id(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid session ID.") from error

def build_router(session_id: str) -> AgentRouter:
    return AgentRouter(get_engine(), session_id=session_id)

def get_long_term_memory() -> LongTermMemoryStore:
    config_path = Path(get_workspace()) / "config.yaml"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        config = {}
    memory_config = config.get("memory", {})
    return LongTermMemoryStore(
        Path(get_workspace()) / "memory",
        backend_name=memory_config.get("backend", "sqlite"),
    )

def load_llm_config() -> dict[str, Any]:
    config_path = Path(get_workspace()) / "config.yaml"
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        config = {}
    return config.get("llm", {})

def required_env_for_provider(provider_name: str) -> str | None:
    provider = provider_name.strip().lower()
    if provider in {"google-genai", "gemini"}:
        return "GOOGLE_API_KEY"
    if provider == "openai":
        return "OPENAI_API_KEY"
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY"
    return None

def ensure_llm_configured() -> None:
    try:
        am = get_account_manager()
        active_acc = am.get_active_account()
        if active_acc:
            budget = active_acc.get("token_budget", -1)
            used = active_acc.get("tokens_used", 0)
            if budget != -1 and used >= budget:
                if am.swap_to_fallback() is True:
                    active_acc = am.get_active_account()
                else:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Token budget exceeded for account '{active_acc['id']}' and no fallback accounts are under budget."
                    )
            api_key = am.resolve_api_key(active_acc)
            if api_key:
                return
    except HTTPException:
        raise
    except Exception:
        pass

    llm_config = load_llm_config()
    provider = llm_config.get("provider", "google-genai")
    required_env = required_env_for_provider(provider)
    if required_env and not os.environ.get(required_env):
        raise HTTPException(
            status_code=503,
            detail=(
                f"{required_env} is not set for provider '{provider}'. "
                "Configure the provider before calling chat, stream, or task endpoints."
            ),
        )

def sse_event(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"



JWT_ISSUER = "las-api"
JWT_AUDIENCE = "las-api"
API_KEYS: dict[str, Any] = {}


def _jwt_secret() -> str:
    secret = os.environ.get("LAS_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("LAS_JWT_SECRET is required and must be at least 32 characters")
    return secret


def _issuer() -> str:
    return os.environ.get("LAS_JWT_ISSUER", JWT_ISSUER)


def _audience() -> str:
    return os.environ.get("LAS_JWT_AUDIENCE", JWT_AUDIENCE)

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode((data + padding).encode('utf-8'))

def generate_jwt(payload: dict) -> str:
    now = int(time.time())
    tenant = payload.get("tenant", payload.get("tenant_id"))
    if not isinstance(tenant, str) or not tenant:
        raise ValueError("tenant claim is required")
    payload = dict(payload)
    payload.setdefault("iss", _issuer())
    payload.setdefault("aud", _audience())
    payload.setdefault("sub", tenant)
    payload.setdefault("tenant", tenant)
    payload.setdefault("tenant_id", tenant)
    payload.setdefault("role", "tenant")
    payload.setdefault("iat", now)
    payload.setdefault("nbf", now)
    payload.setdefault("exp", now + 3600)
    payload.setdefault("jti", uuid.uuid4().hex)
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(_jwt_secret().encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def verify_jwt(token: str) -> dict | None:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        header = json.loads(base64url_decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(_jwt_secret().encode('utf-8'), signing_input, hashlib.sha256).digest()
        expected_sig_b64 = base64url_encode(expected_sig)
        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None
        payload_bytes = base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
        now = time.time()
        required = {"iss", "aud", "sub", "tenant", "iat", "nbf", "exp", "jti"}
        if not required.issubset(payload):
            return None
        if not isinstance(payload["iss"], str) or payload["iss"] != _issuer():
            return None
        audience = payload["aud"]
        if isinstance(audience, str):
            valid_aud = audience == _audience()
        elif isinstance(audience, list):
            valid_aud = bool(audience) and all(isinstance(item, str) for item in audience) and _audience() in audience
        else:
            valid_aud = False
        if not valid_aud:
            return None
        if not isinstance(payload["sub"], str) or not payload["sub"]:
            return None
        if not isinstance(payload["tenant"], str) or not payload["tenant"]:
            return None
        role = payload.get("role")
        scope = payload.get("scope")
        if not isinstance(role, str) and not isinstance(scope, (str, list)):
            return None
        if isinstance(scope, list) and not scope:
            return None
        if isinstance(scope, list) and not all(isinstance(item, str) for item in scope):
            return None
        for name in ("iat", "nbf", "exp"):
            if not isinstance(payload[name], (int, float)) or isinstance(payload[name], bool) or not math.isfinite(payload[name]):
                return None
        if payload["iat"] > now + 30 or payload["nbf"] > now + 30 or payload["exp"] <= now:
            return None
        if not isinstance(payload["jti"], str) or not payload["jti"]:
            return None
        payload["tenant_id"] = payload["tenant"]
        if isinstance(scope, list):
            payload["scope"] = " ".join(scope)
        if "exp" in payload and now > payload["exp"]:
            return None
        return payload
    except Exception:
        return None

def _api_key_principal(api_key: str) -> dict[str, Any] | None:
    configured = API_KEYS.get(api_key)
    if configured is None:
        bootstrap_key = os.environ.get("LAS_BOOTSTRAP_API_KEY")
        if not bootstrap_key or not secrets.compare_digest(api_key, bootstrap_key):
            return None
        return {
            "tenant": os.environ.get("LAS_BOOTSTRAP_TENANT_ID", ""),
            "tenant_id": os.environ.get("LAS_BOOTSTRAP_TENANT_ID", ""),
            "sub": os.environ.get("LAS_BOOTSTRAP_SUBJECT", "bootstrap"),
            "role": os.environ.get("LAS_BOOTSTRAP_ROLE", "bootstrap"),
            "scope": os.environ.get("LAS_BOOTSTRAP_SCOPE", "auth:mint admin:read admin:write"),
        }
    if isinstance(configured, str):
        tenant = configured
        return {"tenant": tenant, "tenant_id": tenant, "sub": tenant, "role": "tenant", "scope": "tenant:read"}
    if isinstance(configured, dict):
        tenant = configured.get("tenant", configured.get("tenant_id"))
        if isinstance(tenant, str) and tenant:
            principal = dict(configured)
            principal["tenant"] = tenant
            principal["tenant_id"] = tenant
            principal.setdefault("sub", tenant)
            return principal
    return None


def get_authenticated_principal(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
    x_enforce_auth: str | None = Header(None)
) -> dict[str, Any]:
    principal: dict[str, Any] | None = None
    if x_api_key:
        principal = _api_key_principal(x_api_key)
        if principal is None:
            raise HTTPException(status_code=401, detail="Invalid API Key")
    elif authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            payload = verify_jwt(token)
            if payload:
                principal = payload
        if principal is None:
            raise HTTPException(status_code=401, detail="Invalid Authorization token")
    else:
        raise HTTPException(status_code=401, detail="Missing Authentication Credentials")

    tenant_id = principal.get("tenant", principal.get("tenant_id"))
    if not isinstance(tenant_id, str) or not tenant_id:
        raise HTTPException(status_code=401, detail="Invalid Authentication principal")

    # Enforce rate-limiting and status checks
    from agent_workspace.core.ledger import FinancialLedger
    from agent_workspace.core.billing import (
        TenantRateLimiter,
        TenantRateLimitError,
        TenantSubscriptionInactiveError,
        TenantQuotaStateUnavailable,
    )

    ledger = FinancialLedger(get_workspace())
    limiter = TenantRateLimiter(ledger)
    try:
        limiter.check_rate_limit(tenant_id)
    except TenantSubscriptionInactiveError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except TenantRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except TenantQuotaStateUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))

    principal["tenant_id"] = tenant_id
    return principal


def get_tenant_context(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
    x_enforce_auth: str | None = Header(None),
) -> str:
    principal = get_authenticated_principal(authorization, x_api_key, x_enforce_auth)
    return principal["tenant_id"]


def require_admin_principal(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
    x_enforce_auth: str | None = Header(None),
) -> dict[str, Any]:
    principal = get_authenticated_principal(authorization, x_api_key, x_enforce_auth)
    role = principal.get("role")
    scopes = principal.get("scope", "")
    if isinstance(scopes, str):
        scopes = set(scopes.split())
    elif isinstance(scopes, list):
        scopes = set(scopes)
    else:
        scopes = set()
    if role not in {"admin", "bootstrap"} and not {"admin", "admin:read", "admin:write"}.intersection(scopes):
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    return principal


def require_admin_write_principal(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None),
    x_enforce_auth: str | None = Header(None),
) -> dict[str, Any]:
    principal = require_admin_principal(authorization, x_api_key, x_enforce_auth)
    role = principal.get("role")
    scopes = principal.get("scope", "")
    if isinstance(scopes, str):
        scopes = set(scopes.split())
    else:
        scopes = set(scopes) if isinstance(scopes, list) else set()
    if role not in {"admin", "bootstrap"} and not {"admin:write", "admin:hijack"}.intersection(scopes):
        raise HTTPException(status_code=403, detail="Forbidden: Admin write authorization required.")
    return principal

async def verify_websocket_tenant(websocket: WebSocket, session_id: str | None = None) -> str | None:
    """
    Unified WebSocket authentication and quota validation helper.
    If unauthorized or rate-limited, accepts the connection, closes it with
    appropriate close code/reason, and returns None.
    Otherwise, returns the validated tenant_id.
    """
    if session_id is not None:
        try:
            validate_session_id(session_id)
        except ValueError:
            await websocket.accept()
            await websocket.close(code=1008, reason="Invalid session ID")
            return None

    params = websocket.query_params
    authorization = websocket.headers.get("authorization")
    api_key = websocket.headers.get("x-api-key")
    if params.get("token") or params.get("api_key"):
        await websocket.accept()
        await websocket.close(code=4001, reason="WebSocket credentials must use headers")
        return None

    principal = None
    if api_key:
        principal = _api_key_principal(api_key)
    elif authorization and authorization.startswith("Bearer "):
        principal = verify_jwt(authorization[7:])
    tenant_id = principal.get("tenant_id", principal.get("tenant")) if principal else None
    if not isinstance(tenant_id, str) or not tenant_id:
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized Tenant")
        return None

    from agent_workspace.core.ledger import FinancialLedger
    from agent_workspace.core.billing import (
        TenantRateLimiter,
        TenantRateLimitError,
        TenantSubscriptionInactiveError,
        TenantQuotaStateUnavailable,
    )
    from agent_workspace.core.swarm_coordinator import SwarmCoordinator
    from agent_workspace.core.rate_limit import RateLimitStateUnavailable

    ledger = FinancialLedger(get_workspace())
    limiter = TenantRateLimiter(ledger)
    try:
        limiter.check_rate_limit(tenant_id)
        SwarmCoordinator.verify_tenant_credit(get_workspace(), tenant_id)
    except TenantSubscriptionInactiveError as e:
        await websocket.accept()
        await websocket.close(code=4003, reason=str(e))
        return None
    except TenantRateLimitError as e:
        await websocket.accept()
        await websocket.close(code=4029, reason=str(e))
        return None
    except QuotaExceededError as e:
        await websocket.accept()
        await websocket.close(code=4029, reason=str(e))
        return None
    except (TenantQuotaStateUnavailable, RateLimitStateUnavailable):
        await websocket.accept()
        await websocket.close(code=1013, reason="Quota state unavailable")
        return None
    except Exception:
        await websocket.accept()
        await websocket.close(code=1013, reason="Quota validation unavailable")
        return None

    await websocket.accept()
    return tenant_id
