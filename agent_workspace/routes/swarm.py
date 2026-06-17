import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from agent_workspace.routes.dependencies import get_tenant_context, verify_jwt, API_KEYS, workspace, get_workspace
from agent_workspace.routes.schemas import ScaleRequest, BillingPolicyRequest, ResumeSessionRequest, ReplayCleanRequest, GovernanceVoteRequest

logger = logging.getLogger("api.swarm")

router = APIRouter()

@router.get("/v1/swarm/nodes")
async def get_swarm_nodes(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.swarm_coordinator import SwarmCoordinator
    return {"status": "success", "nodes": SwarmCoordinator.get_active_nodes()}

@router.post("/v1/swarm/scale")
async def scale_swarm(req: ScaleRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.swarm_coordinator import SwarmCoordinator
    res = SwarmCoordinator.simulate_scaling(req.role, req.direction)
    return res

@router.get("/v1/swarm/health")
async def get_swarm_health(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.swarm_coordinator import SwarmCoordinator
    nodes = SwarmCoordinator.get_active_nodes()
    failures = SwarmCoordinator.get_failure_logs()
    active_roles = list(set(n["role"] for n in nodes))
    return {
        "status": "success",
        "healthy": len(nodes) > 0 or len(failures) == 0,
        "active_nodes_count": len(nodes),
        "active_roles": active_roles,
        "failures_count": len(failures),
        "failure_logs": failures
    }

@router.get("/v1/swarm/peers")
async def get_swarm_peers(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.p2p_router import get_p2p_router
    p2p_router = get_p2p_router()
    peers_list = []
    for peer_id, info in p2p_router.peers.items():
        peers_list.append({
            "node_id": peer_id,
            "role": info.get("role", "unknown"),
            "address": f"{info.get('host')}:{info.get('port')}",
            "latency_ms": info.get("latency", 0.0),
            "status": info.get("status", "disconnected")
        })
    return {"status": "success", "peers": peers_list}

@router.get("/v1/swarm/billing/status")
async def get_swarm_billing_status(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.ledger import FinancialLedger
    ledger = FinancialLedger(get_workspace())
    
    import sqlite3
    conn = sqlite3.connect(str(ledger.db_path))
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT credits, max_budget, routing_policy FROM tenant_credit_budget WHERE tenant_id = ?",
            (tenant_id,)
        )
        row = cursor.fetchone()
        if row:
            credits = row["credits"]
            max_budget = row["max_budget"]
            routing_policy = row["routing_policy"]
        else:
            credits = 100.0
            max_budget = 100.0
            routing_policy = "downscale"
            conn.execute(
                "INSERT OR IGNORE INTO tenant_credit_budget (tenant_id, credits, max_budget, routing_policy) VALUES (?, ?, ?, ?)",
                (tenant_id, credits, max_budget, routing_policy)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Error fetching swarm billing status for tenant {tenant_id}: {e}")
        credits = 100.0
        max_budget = 100.0
        routing_policy = "downscale"
    finally:
        conn.close()

    records = ledger.get_all_records(tenant_id=tenant_id)
    history = [dict(r) for r in records]

    return {
        "tenant_id": tenant_id,
        "credits": credits,
        "max_budget": max_budget,
        "routing_policy": routing_policy,
        "history": history
    }

@router.post("/v1/swarm/billing/policy")
async def configure_billing_policy(req: BillingPolicyRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.ledger import FinancialLedger
    ledger = FinancialLedger(get_workspace())
    import sqlite3
    conn = sqlite3.connect(str(ledger.db_path))
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT tenant_id FROM tenant_credit_budget WHERE tenant_id = ?", (tenant_id,))
        if not cursor.fetchone():
            conn.execute(
                "INSERT INTO tenant_credit_budget (tenant_id, credits, max_budget, routing_policy) VALUES (?, 100.0, 100.0, 'downscale')",
                (tenant_id,)
            )
            conn.commit()
            
        updates = []
        params = []
        if req.routing_policy is not None:
            updates.append("routing_policy = ?")
            params.append(req.routing_policy)
        if req.credits is not None:
            updates.append("credits = ?")
            params.append(req.credits)
        if req.max_budget is not None:
            updates.append("max_budget = ?")
            params.append(req.max_budget)
            
        if updates:
            params.append(tenant_id)
            query = f"UPDATE tenant_credit_budget SET {', '.join(updates)} WHERE tenant_id = ?"
            conn.execute(query, tuple(params))
            conn.commit()
            
        cursor = conn.execute(
            "SELECT credits, max_budget, routing_policy FROM tenant_credit_budget WHERE tenant_id = ?",
            (tenant_id,)
        )
        row = cursor.fetchone()
        return {
            "status": "success",
            "credits": row["credits"],
            "max_budget": row["max_budget"],
            "routing_policy": row["routing_policy"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update policy: {e}")
    finally:
        conn.close()

@router.get("/v1/swarm/sessions")
async def get_swarm_sessions(tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant" and tenant_id != "default_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    
    from agent_workspace.core.broker import get_broker, RedisSwarmBroker
    broker = get_broker(workspace_path=get_workspace())
    sessions_info = []
    
    if isinstance(broker, RedisSwarmBroker) and broker.client:
        try:
            keys = await broker.client.keys("swarm:session:*:checkpoint")
            for k in keys:
                data_str = await broker.client.get(k)
                if data_str:
                    sessions_info.append(json.loads(data_str))
        except Exception as e:
            logger.error(f"Error reading checkpoints from Redis: {e}")
    elif hasattr(broker, "kv_store"):
        for k, v in broker.kv_store.items():
            if k.startswith("swarm:session:") and k.endswith(":checkpoint"):
                sessions_info.append(json.loads(v))
                
    return {"status": "success", "sessions": sessions_info}

@router.post("/v1/swarm/sessions/resume")
async def resume_session_endpoint(req: ResumeSessionRequest, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant" and tenant_id != "default_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
        
    from agent_workspace.core.broker import get_broker, RedisSwarmBroker
    from agent_workspace.core.swarm_coordinator import SwarmCoordinator
        
    broker = get_broker(workspace_path=get_workspace())
    redis_key = f"swarm:session:{req.session_id}:checkpoint"
    data_str = None
    
    if hasattr(broker, "kv_store"):
        data_str = broker.kv_store.get(redis_key)
    elif isinstance(broker, RedisSwarmBroker) and broker.client:
        try:
            data_str = await broker.client.get(redis_key)
        except Exception:
            pass
            
    if not data_str:
        raise HTTPException(status_code=404, detail=f"No checkpoint found for session '{req.session_id}'")
        
    checkpoint = json.loads(data_str)
    executing_node = checkpoint.get("node_id")
    
    if executing_node:
        SwarmCoordinator.mark_node_offline(executing_node, reason="manual_failover")
        
    # Re-publish/sync checkpoint
    sync_msg = {
        "type": "checkpoint_sync",
        "session_id": req.session_id,
        "checkpoint": checkpoint
    }
    await broker.publish("swarm:session:checkpoint:sync", sync_msg)
    
    return {
        "status": "success",
        "message": f"Forced failover and resumption triggered for session '{req.session_id}'",
        "session_id": req.session_id,
        "previous_node": executing_node
    }

@router.get("/v1/swarm/replays/{session_id}")
async def get_swarm_replay(session_id: str, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant" and tenant_id != "default_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
        
    from agent_workspace.core.replay_logger import ReplayLogger
    timeline = ReplayLogger.get_session_timeline(get_workspace(), session_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail="Session replay not found")
        
    return {
        "status": "success",
        "session_id": session_id,
        "timeline": timeline
    }

@router.post("/v1/swarm/replays/clean")
async def clean_swarm_replays(req: ReplayCleanRequest, tenant_id: str = Depends(get_tenant_context)):
    if tenant_id != "admin_tenant" and tenant_id != "default_tenant":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
        
    from agent_workspace.core.replay_logger import ReplayLogger
    ttl_days = req.ttl_days if req.ttl_days is not None else 7
    purged_count = ReplayLogger.clean_replays(get_workspace(), ttl_days)
    
    return {
        "status": "success",
        "purged_count": purged_count
    }

@router.websocket("/v1/swarm/telemetry/ws")
async def swarm_telemetry_ws_endpoint(websocket: WebSocket):
    params = websocket.query_params
    session_id = params.get("session_id")

    from agent_workspace.routes.dependencies import verify_websocket_tenant
    tenant_id = await verify_websocket_tenant(websocket, session_id)
    if not tenant_id:
        return


    from agent_workspace.observability import get_telemetry_router
    router_telemetry = get_telemetry_router(get_workspace())

    try:
        while True:
            metrics = router_telemetry.get_metrics(session_id)
            if not metrics:
                router_telemetry.record_metric(session_id or "global-session", latency_ms=100.0, ws_latency_ms=30.0)
                metrics = router_telemetry.get_metrics(session_id)
                
            latest_metric = metrics[-1] if metrics else {}
            
            try:
                import psutil
                latest_metric["cpu_percent"] = round(psutil.cpu_percent(), 2)
                latest_metric["memory_mb"] = round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
            except Exception:
                pass

            # Query Stripe/billing info for the tenant
            billing_tier = "Standard"
            credits_remaining = 100.0
            billing_status = "active"
            try:
                import sqlite3
                from agent_workspace.core.ledger import FinancialLedger
                fl = FinancialLedger(get_workspace())
                conn = sqlite3.connect(str(fl.db_path))
                conn.row_factory = sqlite3.Row
                try:
                    cursor = conn.execute("SELECT credits FROM tenant_credit_budget WHERE tenant_id = ?", (tenant_id,))
                    row = cursor.fetchone()
                    if row:
                        credits_remaining = float(row["credits"])
                    
                    cursor = conn.execute("SELECT status, stripe_subscription_id FROM tenant_subscription_status WHERE tenant_id = ?", (tenant_id,))
                    row = cursor.fetchone()
                    if row:
                        billing_status = row["status"]
                        if row["stripe_subscription_id"] and "premium" in row["stripe_subscription_id"].lower():
                            billing_tier = "Premium"
                        else:
                            billing_tier = "Standard"
                finally:
                    conn.close()
            except Exception as e:
                logger.error("Failed to query billing info for telemetry: %s", e)

            latest_metric["billing_tier"] = billing_tier
            latest_metric["credits_remaining"] = credits_remaining
            latest_metric["billing_status"] = billing_status

            payload = {
                "status": "success",
                "session_id": session_id,
                "telemetry": latest_metric,
                "billing_tier": billing_tier,
                "credits_remaining": credits_remaining,
                "billing_status": billing_status
            }
            await websocket.send_json(payload)

            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                try:
                    msg = json.loads(data)
                    if "session_id" in msg:
                        session_id = msg["session_id"]
                except Exception:
                    pass
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        logger.info("Telemetry WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in Telemetry WebSocket: {e}")
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/v1/swarm/governance/rules")
async def get_governance_rules(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.governance import GovernanceManager
        
    try:
        proposals = GovernanceManager.get_all_proposals(get_workspace())
        active_rules = GovernanceManager.get_active_rules(get_workspace())
        return {
            "status": "success",
            "proposals": proposals,
            "active_rules": active_rules
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error getting governance rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/swarm/governance/vote")
async def cast_governance_vote(req: GovernanceVoteRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.governance import GovernanceManager
        
    try:
        res = GovernanceManager.cast_vote(
            workspace_path=get_workspace(),
            proposal_id=req.proposal_id,
            role=req.role,
            vote=req.vote,
            signature=req.signature
        )
        if res:
            return {"status": "success", "message": "Vote cast successfully"}
        else:
            raise HTTPException(status_code=400, detail="Vote failed signature check or validation")
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error casting governance vote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

