import os
import sys
import json
import logging
import sqlite3
import time
import hmac
import hashlib
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Header, Request

from agent_workspace.routes.dependencies import (
    get_tenant_context,
    get_authenticated_principal,
    require_admin_principal,
    require_admin_write_principal,
    get_workspace,
    API_KEYS,
    verify_jwt,
    generate_jwt
)
from agent_workspace.routes.schemas import AuthTokenRequest

logger = logging.getLogger(__name__)

router = APIRouter()


from pydantic import BaseModel


class RotateKeyRequest(BaseModel):
    tenant_id: str

class UpdateSubRequest(BaseModel):
    tenant_id: str
    status: str

class HijackRequest(BaseModel):
    hijack_value: str


# Stripe configurations & webhook validation
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_WEBHOOK_TOLERANCE_SECONDS = int(os.getenv("STRIPE_WEBHOOK_TOLERANCE_SECONDS", "300"))
STRIPE_TENANT_SUBSCRIPTION_ITEMS = {
    "tenant_a": os.getenv("STRIPE_SUB_ITEM_TENANT_A"),
    "tenant_b": os.getenv("STRIPE_SUB_ITEM_TENANT_B"),
    "admin_tenant": os.getenv("STRIPE_SUB_ITEM_ADMIN"),
}


def verify_stripe_signature(payload_bytes: bytes, header: str, secret: str) -> bool:
    if not header or not secret:
        return False
    timestamp_value = next(
        (part.split("=", 1)[1].strip() for part in header.split(",")
         if part.strip().startswith("t=") and "=" in part),
        None,
    )
    signatures = [
        part.split("=", 1)[1].strip()
        for part in header.split(",")
        if part.strip().startswith("v1=") and "=" in part
    ]
    if not timestamp_value or not signatures:
        return False
    try:
        timestamp = int(timestamp_value)
    except ValueError:
        return False
    if abs(int(time.time()) - timestamp) > STRIPE_WEBHOOK_TOLERANCE_SECONDS:
        return False
    signed_payload = f"{timestamp_value}.".encode("utf-8") + payload_bytes
    computed = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(computed, signature) for signature in signatures)


def _resolve_stripe_tenant(status_mgr: Any, event_type: str, data_obj: dict[str, Any]) -> str | None:
    metadata = data_obj.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="Invalid Stripe metadata")
    metadata_tenant = metadata.get("tenant_id")
    if metadata_tenant is not None and not isinstance(metadata_tenant, str):
        raise HTTPException(status_code=400, detail="Invalid Stripe tenant binding")
    customer_id = data_obj.get("customer")
    subscription_id = data_obj.get("id") if event_type.startswith("customer.subscription.") else data_obj.get("subscription")
    mapped_tenants = {
        tenant
        for tenant in (
            status_mgr.get_tenant_by_stripe_customer(customer_id) if isinstance(customer_id, str) else None,
            status_mgr.get_tenant_by_stripe_subscription(subscription_id) if isinstance(subscription_id, str) else None,
        )
        if tenant
    }
    if len(mapped_tenants) > 1 or (metadata_tenant and mapped_tenants and metadata_tenant not in mapped_tenants):
        raise HTTPException(status_code=400, detail="Stripe event tenant binding conflict")
    if metadata_tenant:
        return metadata_tenant
    if mapped_tenants:
        return next(iter(mapped_tenants))
    return None


async def sync_billing_to_stripe():
    from agent_workspace.core.ledger import FinancialLedger
    ledger = FinancialLedger(get_workspace())
    stripe_api_key = STRIPE_API_KEY
    legacy_api = sys.modules.get("api") or sys.modules.get("agent_workspace.api")
    if legacy_api is not None:
        stripe_api_key = getattr(legacy_api, "STRIPE_API_KEY", stripe_api_key)
    import sqlite3
    db_path = ledger.db_path
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stripe_sync_metadata (
                tenant_id TEXT PRIMARY KEY,
                last_synced_id INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()

        cursor = conn.execute("SELECT tenant_id, last_synced_id FROM stripe_sync_metadata")
        sync_state = {row["tenant_id"]: row["last_synced_id"] for row in cursor.fetchall()}
        
        cursor = conn.execute("SELECT DISTINCT tenant_id FROM financial_ledger")
        tenants = [row["tenant_id"] for row in cursor.fetchall()]
        
        for t_id in tenants:
            last_id = sync_state.get(t_id, 0)
            
            cursor = conn.execute(
                "SELECT id, total_tokens, cost FROM financial_ledger WHERE tenant_id = ? AND id > ? ORDER BY id ASC",
                (t_id, last_id)
            )
            records = cursor.fetchall()
            if not records:
                continue
            
            total_qty = sum(r["total_tokens"] for r in records)
            max_id = max(r["id"] for r in records)
            
            sub_item_id = STRIPE_TENANT_SUBSCRIPTION_ITEMS.get(t_id)
            if not stripe_api_key or not sub_item_id:
                continue
            timestamp = int(time.time())
            
            import httpx
            headers = {
                "Authorization": f"Bearer {stripe_api_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            body = f"quantity={total_qty}&timestamp={timestamp}&action=increment"
            
            if stripe_api_key.lower().startswith("mock"):
                continue
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"https://api.stripe.com/v1/subscription_items/{sub_item_id}/usage_records",
                        headers=headers,
                        content=body,
                        timeout=10.0
                    )
                    if resp.status_code in (200, 201):
                        success = True
                    else:
                        logger.error(f"Stripe API error: {resp.status_code} - {resp.text}")
                        success = False
            except Exception as ex:
                logger.error(f"Failed to post billing usage to Stripe: {ex}")
                success = False
            
            if success:
                conn.execute(
                    "INSERT OR REPLACE INTO stripe_sync_metadata (tenant_id, last_synced_id) VALUES (?, ?)",
                    (t_id, max_id)
                )
                conn.commit()
                logger.info(f"Synced {total_qty} tokens to Stripe for '{t_id}'. Updated last_synced_id to {max_id}.")
    except Exception as e:
        logger.error(f"Stripe sync billing error: {e}")
    finally:
        conn.close()


async def start_stripe_billing_scheduler():
    while True:
        try:
            await sync_billing_to_stripe()
        except Exception as e:
            logger.error(f"Error in Stripe billing scheduler: {e}")
        await asyncio.sleep(60)


@router.post("/v1/billing/stripe/webhook")
async def stripe_webhook(request: Request):
    body_bytes = await request.body()
    headers = request.headers
    signature = headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")
    
    if not verify_stripe_signature(body_bytes, signature, STRIPE_WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid Stripe signature")
        
    try:
        event = json.loads(body_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    if not isinstance(event, dict) or not isinstance(event.get("id"), str) or not event["id"]:
        raise HTTPException(status_code=400, detail="Stripe event id is required")
    event_type = event.get("type", "unknown")
    if not isinstance(event_type, str):
        raise HTTPException(status_code=400, detail="Invalid Stripe event type")
    data = event.get("data", {})
    data_obj = data.get("object", {}) if isinstance(data, dict) else {}
    if not isinstance(data_obj, dict):
        raise HTTPException(status_code=400, detail="Invalid Stripe event object")
    from agent_workspace.core.ledger import FinancialLedger
    from agent_workspace.core.billing import TenantStatusManager
    ledger = FinancialLedger(get_workspace())
    status_mgr = TenantStatusManager(ledger)
    known_event_types = {
        "customer.subscription.created",
        "customer.subscription.deleted",
        "customer.subscription.updated",
        "invoice.payment_failed",
    }
    tenant_id = _resolve_stripe_tenant(status_mgr, event_type, data_obj)
    if event_type in known_event_types and not tenant_id:
        raise HTTPException(status_code=400, detail="Stripe event tenant binding is required")
    tenant_id = tenant_id or "admin_tenant"
    payload_hash = hashlib.sha256(body_bytes).hexdigest()
    existing_event = ledger.get_stripe_webhook_event(event["id"])
    if existing_event:
        if existing_event[0] != payload_hash or existing_event[1] != tenant_id:
            raise HTTPException(status_code=409, detail="Stripe event id was already used")
        return {"status": "duplicate", "event": event_type}
    if not ledger.claim_stripe_webhook_event(event["id"], payload_hash, tenant_id):
        return {"status": "duplicate", "event": event_type}

    from agent_workspace.core.audit_ledger import AuditLedger
    audit = AuditLedger(get_workspace())
    audit.record_event("system_call", {
        "event": "stripe_webhook",
        "stripe_event_id": event["id"],
        "stripe_event_type": event_type,
        "tenant_id": tenant_id,
    }, tenant_id="admin_tenant")

    stripe_customer_id = data_obj.get("customer")
    stripe_subscription_id = data_obj.get("id") if event_type.startswith("customer.subscription.") else data_obj.get("subscription")
    if event_type == "customer.subscription.created":
        status_mgr.update_tenant_status(
            tenant_id=tenant_id,
            status="active",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id
        )
    elif event_type == "customer.subscription.deleted":
        status_mgr.update_tenant_status(
            tenant_id=tenant_id,
            status="canceled",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id
        )
    elif event_type == "customer.subscription.updated":
        stripe_status = data_obj.get("status")
        if stripe_status in ("active", "trialing"):
            status = "active"
        elif stripe_status in ("past_due", "unpaid", "paused"):
            status = "frozen"
        elif stripe_status in ("canceled", "incomplete_expired"):
            status = "canceled"
        else:
            status = "frozen"
        status_mgr.update_tenant_status(
            tenant_id=tenant_id,
            status=status,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id
        )
    elif event_type == "invoice.payment_failed":
        status_mgr.update_tenant_status(
            tenant_id=tenant_id,
            status="frozen",
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id
        )
        
    return {"status": "success", "event": event_type}


@router.post("/v1/auth/token")
async def generate_auth_token(req: AuthTokenRequest, principal: dict[str, Any] = Depends(get_authenticated_principal)):
    principal_tenant = principal["tenant_id"]
    if req.tenant_id != principal_tenant:
        raise HTTPException(status_code=403, detail="Token tenant must match authenticated principal")
    role = principal.get("role", "tenant")
    scope = principal.get("scope", "tenant:read")
    if role not in {"admin", "bootstrap"} and "auth:mint" not in (scope.split() if isinstance(scope, str) else scope):
        raise HTTPException(status_code=403, detail="Token minting requires bootstrap or admin authorization")
    payload = {
        "tenant": principal_tenant,
        "tenant_id": principal_tenant,
        "sub": principal.get("sub", principal_tenant),
        "role": role,
        "scope": scope,
        "exp": time.time() + 3600
    }
    try:
        token = generate_jwt(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="JWT signing is not configured") from exc
    return {"access_token": token, "token_type": "bearer"}


@router.get("/v1/admin/tenants")
async def admin_get_tenants(principal: dict[str, Any] = Depends(require_admin_principal)):
    
    from agent_workspace.core.ledger import FinancialLedger
    ledger = FinancialLedger(get_workspace())
    
    conn = sqlite3.connect(str(ledger.db_path))
    conn.row_factory = sqlite3.Row
    db_tenants = {}
    try:
        cursor = conn.execute("SELECT * FROM tenant_subscription_status")
        for row in cursor.fetchall():
            db_tenants[row["tenant_id"]] = {
                "tenant_id": row["tenant_id"],
                "status": row["status"],
                "stripe_customer_id": row["stripe_customer_id"],
                "stripe_subscription_id": row["stripe_subscription_id"],
                "last_updated": row["last_updated"]
            }
    except Exception as e:
        logger.error(f"Error querying tenant status: {e}")
    finally:
        conn.close()

    all_tenants = []
    seen_tenants = set()
    configured_tenants = {value if isinstance(value, str) else value.get("tenant_id", value.get("tenant")) for value in API_KEYS.values()}
    configured_tenants.discard(None)
    configured_tenants.update(db_tenants)
    for t_id in sorted(configured_tenants):
        if t_id in seen_tenants:
            continue
        seen_tenants.add(t_id)
        
        total_tokens = 0
        total_cost = 0.0
        try:
            conn = sqlite3.connect(str(ledger.db_path))
            cursor = conn.execute("SELECT SUM(total_tokens), SUM(cost) FROM financial_ledger WHERE tenant_id = ?", (t_id,))
            row = cursor.fetchone()
            if row:
                total_tokens = row[0] if row[0] is not None else 0
                total_cost = row[1] if row[1] is not None else 0.0
        except Exception:
            pass
        finally:
            conn.close()

        tokens_last_min = 0
        try:
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            one_minute_ago = (now - timedelta(seconds=60)).isoformat()
            conn = sqlite3.connect(str(ledger.db_path))
            cursor = conn.execute("SELECT SUM(total_tokens) FROM financial_ledger WHERE tenant_id = ? AND timestamp >= ?", (t_id, one_minute_ago))
            row = cursor.fetchone()
            if row and row[0] is not None:
                tokens_last_min = row[0]
        except Exception:
            pass
        finally:
            conn.close()

        from datetime import datetime, timezone
        status_info = db_tenants.get(t_id, {
            "tenant_id": t_id,
            "status": "active",
            "stripe_customer_id": None,
            "stripe_subscription_id": None,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })

        all_tenants.append({
            **status_info,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "tokens_last_minute": tokens_last_min
        })

    return {"status": "success", "tenants": all_tenants}


@router.post("/v1/admin/tenants/rotate-key")
async def admin_rotate_key(req: RotateKeyRequest, principal: dict[str, Any] = Depends(require_admin_write_principal)):
    
    import secrets
    new_key = f"key-{req.tenant_id}-{secrets.token_hex(4)}"
    
    keys_to_delete = [
        k for k, v in API_KEYS.items()
        if (v if isinstance(v, str) else v.get("tenant_id", v.get("tenant"))) == req.tenant_id
    ]
    for k in keys_to_delete:
        del API_KEYS[k]
    
    API_KEYS[new_key] = req.tenant_id
    return {"status": "success", "tenant_id": req.tenant_id, "one_time_api_key": new_key}


@router.post("/v1/admin/tenants/update-subscription")
async def admin_update_subscription(req: UpdateSubRequest, principal: dict[str, Any] = Depends(require_admin_write_principal)):
    
    from agent_workspace.core.ledger import FinancialLedger
    from agent_workspace.core.billing import TenantStatusManager
        
    ledger = FinancialLedger(get_workspace())
    status_mgr = TenantStatusManager(ledger)
    
    status_mgr.update_tenant_status(
        tenant_id=req.tenant_id,
        status=req.status,
        stripe_customer_id=f"cust-{req.tenant_id}",
        stripe_subscription_id=f"sub-{req.tenant_id}"
    )
    return {"status": "success", "tenant_id": req.tenant_id, "status": req.status}


@router.post("/v1/sessions/{session_id}/pause")
@router.post("/v1/session/{session_id}/pause")
async def pause_session_endpoint(session_id: str, principal: dict[str, Any] = Depends(require_admin_write_principal)):
    from agent_workspace.core.router import AgentRouter
    AgentRouter.pause_session(session_id)
    return {"status": "success", "session_id": session_id, "swarm_status": "paused"}


@router.post("/v1/sessions/{session_id}/resume")
@router.post("/v1/session/{session_id}/resume")
async def resume_session_endpoint(session_id: str, principal: dict[str, Any] = Depends(require_admin_write_principal)):
    from agent_workspace.core.router import AgentRouter
    AgentRouter.resume_session(session_id)
    return {"status": "success", "session_id": session_id, "swarm_status": "running"}


@router.post("/v1/sessions/{session_id}/hijack")
@router.post("/v1/session/{session_id}/hijack")
async def hijack_session_endpoint(session_id: str, req: HijackRequest, principal: dict[str, Any] = Depends(require_admin_write_principal)):
    from agent_workspace.core.router import ACTIVE_APPROVALS
        
    approval_req = ACTIVE_APPROVALS.get(session_id)
    if not approval_req:
        raise HTTPException(status_code=404, detail=f"No pending HITL gate for session '{session_id}' to hijack.")
    
    future = approval_req["future"]
    if not future.done():
        future.set_result({"hijacked": True, "hijack_value": req.hijack_value})
        return {"status": "success", "session_id": session_id, "hijack_value": req.hijack_value}
    return {"status": "already_resolved", "session_id": session_id}


@router.get("/v1/billing/saas/invoice")
async def get_saas_invoice(filter_id: str | None = None, markup_multiplier: float = 1.5, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.ledger import FinancialLedger
    from agent_workspace.core.billing import SaaSBillingTracker
        
    ledger = FinancialLedger(get_workspace())
    tracker = SaaSBillingTracker(ledger)
    invoice = tracker.get_saas_invoice(filter_id=filter_id, markup_multiplier=markup_multiplier, tenant_id=tenant_id)
    return invoice


@router.get("/v1/workspace/config")
async def get_workspace_config(tenant_id: str = Depends(get_tenant_context)):
    project_root = Path(get_workspace()).parent
    config_file = project_root / "workspace" / "workspace.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail="Workspace configuration file not found")
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read workspace config: {e}")
        
    tasks = data.get("tasks", [])
    filtered_tasks = []
    for task in tasks:
        t_id = task.get("tenant_id", "default_tenant")
        if t_id == tenant_id:
            filtered_tasks.append(task)
            
    data["tasks"] = filtered_tasks
    return data
