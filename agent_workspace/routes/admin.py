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
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "mock_stripe_api_key")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "mock_stripe_webhook_secret")
STRIPE_TENANT_SUBSCRIPTION_ITEMS = {
    "tenant_a": os.getenv("STRIPE_SUB_ITEM_TENANT_A", "si_mock_tenant_a"),
    "tenant_b": os.getenv("STRIPE_SUB_ITEM_TENANT_B", "si_mock_tenant_b"),
    "admin_tenant": os.getenv("STRIPE_SUB_ITEM_ADMIN", "si_mock_admin"),
}


def verify_stripe_signature(payload_bytes: bytes, header: str, secret: str) -> bool:
    if not header or not secret:
        return False
    try:
        pairs = {}
        for part in header.split(','):
            kv = part.split('=', 1)
            if len(kv) == 2:
                pairs[kv[0].strip()] = kv[1].strip()
        t = pairs.get('t')
        v1 = pairs.get('v1')
        if not t or not v1:
            return False
            
        signed_payload = f"{t}.".encode('utf-8') + payload_bytes
        computed = hmac.new(secret.encode('utf-8'), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, v1)
    except Exception as e:
        logger.error(f"Stripe webhook verification error: {e}")
        return False


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
            
            sub_item_id = STRIPE_TENANT_SUBSCRIPTION_ITEMS.get(t_id, f"si_mock_{t_id}")
            timestamp = int(time.time())
            
            import httpx
            headers = {
                "Authorization": f"Bearer {stripe_api_key}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            body = f"quantity={total_qty}&timestamp={timestamp}&action=increment"
            
            if stripe_api_key.startswith("mock"):
                logger.info(f"[Mock Stripe Billing Sync] Tenant: {t_id}, SubItem: {sub_item_id}, Qty: {total_qty}")
                success = True
            else:
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
        event = json.loads(body_bytes.decode('utf-8'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    event_type = event.get("type", "unknown")
    logger.info(f"Received Stripe webhook event: {event_type}")
    
    from agent_workspace.core.audit_ledger import AuditLedger
    audit = AuditLedger(get_workspace())
    audit.record_event("system_call", {
        "event": "stripe_webhook",
        "stripe_event_type": event_type,
        "payload": event
    }, tenant_id="admin_tenant")
    
    data_obj = event.get("data", {}).get("object", {})
    stripe_customer_id = data_obj.get("customer")
    stripe_subscription_id = data_obj.get("id") if event_type.startswith("customer.subscription.") else data_obj.get("subscription")
    
    tenant_id = data_obj.get("metadata", {}).get("tenant_id")
    
    from agent_workspace.core.ledger import FinancialLedger
    from agent_workspace.core.billing import TenantStatusManager
    ledger = FinancialLedger(get_workspace())
    status_mgr = TenantStatusManager(ledger)
    
    if not tenant_id and stripe_subscription_id:
        tenant_id = status_mgr.get_tenant_by_stripe_subscription(stripe_subscription_id)
    if not tenant_id and stripe_customer_id:
        tenant_id = status_mgr.get_tenant_by_stripe_customer(stripe_customer_id)
        
    if not tenant_id:
        if stripe_customer_id:
            if "tenant_a" in stripe_customer_id:
                tenant_id = "tenant_a"
            elif "tenant_b" in stripe_customer_id:
                tenant_id = "tenant_b"
            else:
                tenant_id = stripe_customer_id
        elif stripe_subscription_id:
            if "tenant_a" in stripe_subscription_id:
                tenant_id = "tenant_a"
            elif "tenant_b" in stripe_subscription_id:
                tenant_id = "tenant_b"
            else:
                tenant_id = stripe_subscription_id
        else:
            tenant_id = "default_tenant"
            
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
async def generate_auth_token(req: AuthTokenRequest):
    payload = {
        "tenant_id": req.tenant_id,
        "exp": time.time() + 3600
    }
    token = generate_jwt(payload)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/v1/admin/tenants")
async def admin_get_tenants(tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    
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
    for key, t_id in API_KEYS.items():
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
            "stripe_customer_id": "mock_customer_id" if t_id != "admin_tenant" else None,
            "stripe_subscription_id": "mock_sub_id" if t_id != "admin_tenant" else None,
            "last_updated": datetime.now(timezone.utc).isoformat()
        })

        all_tenants.append({
            **status_info,
            "api_key": key,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "tokens_last_minute": tokens_last_min
        })

    return {"status": "success", "tenants": all_tenants}


@router.post("/v1/admin/tenants/rotate-key")
async def admin_rotate_key(req: RotateKeyRequest, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    
    import secrets
    new_key = f"key-{req.tenant_id}-{secrets.token_hex(4)}"
    
    keys_to_delete = [k for k, v in API_KEYS.items() if v == req.tenant_id]
    for k in keys_to_delete:
        del API_KEYS[k]
    
    API_KEYS[new_key] = req.tenant_id
    return {"status": "success", "tenant_id": req.tenant_id, "api_key": new_key}


@router.post("/v1/admin/tenants/update-subscription")
async def admin_update_subscription(req: UpdateSubRequest, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    
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
async def pause_session_endpoint(session_id: str, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    from agent_workspace.core.router import AgentRouter
    AgentRouter.pause_session(session_id)
    return {"status": "success", "session_id": session_id, "swarm_status": "paused"}


@router.post("/v1/sessions/{session_id}/resume")
@router.post("/v1/session/{session_id}/resume")
async def resume_session_endpoint(session_id: str, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    from agent_workspace.core.router import AgentRouter
    AgentRouter.resume_session(session_id)
    return {"status": "success", "session_id": session_id, "swarm_status": "running"}


@router.post("/v1/sessions/{session_id}/hijack")
@router.post("/v1/session/{session_id}/hijack")
async def hijack_session_endpoint(session_id: str, req: HijackRequest, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
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
