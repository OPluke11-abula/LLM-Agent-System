import os
import sys
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from agent_workspace.routes.dependencies import get_tenant_context, workspace
from agent_workspace.routes.schemas import CrossCloudRevokeRequest, CrossCloudReinstateRequest

logger = logging.getLogger("api.cross_cloud")

router = APIRouter()

@router.get("/v1/cross-cloud/cert/status")
async def get_cross_cloud_cert_status(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.cross_cloud_gateway import CROSS_CLOUD_GATEWAY
    now = datetime.now(timezone.utc)
    seconds_remaining = 0
    status = "expired"

    if CROSS_CLOUD_GATEWAY.cert_expiry:
        seconds_remaining = max(0.0, (CROSS_CLOUD_GATEWAY.cert_expiry - now).total_seconds())
        if seconds_remaining > 360:
            status = "active"
        elif seconds_remaining > 0:
            status = "expiring"

    return {
        "status": "success",
        "cert_sha": CROSS_CLOUD_GATEWAY.cert_sha,
        "expiration": CROSS_CLOUD_GATEWAY.cert_expiry.isoformat() if CROSS_CLOUD_GATEWAY.cert_expiry else None,
        "seconds_remaining": seconds_remaining,
        "cert_status": status
    }

@router.post("/v1/cross-cloud/cert/rotate")
async def rotate_cross_cloud_cert(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.cross_cloud_gateway import CROSS_CLOUD_GATEWAY
    CROSS_CLOUD_GATEWAY.rotate_certificate()
    now = datetime.now(timezone.utc)
    seconds_remaining = max(0.0, (CROSS_CLOUD_GATEWAY.cert_expiry - now).total_seconds()) if CROSS_CLOUD_GATEWAY.cert_expiry else 0.0

    return {
        "status": "success",
        "cert_sha": CROSS_CLOUD_GATEWAY.cert_sha,
        "expiration": CROSS_CLOUD_GATEWAY.cert_expiry.isoformat() if CROSS_CLOUD_GATEWAY.cert_expiry else None,
        "seconds_remaining": seconds_remaining,
        "cert_status": "active"
    }

@router.post("/v1/cross-cloud/revoke")
async def revoke_cross_cloud_cert(req: CrossCloudRevokeRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.cross_cloud_gateway import CROSS_CLOUD_GATEWAY
    revoked_count = 0
    if req.client_cert_sha:
        CROSS_CLOUD_GATEWAY.revoked_certs.add(req.client_cert_sha)
        try:
            CROSS_CLOUD_GATEWAY.audit_ledger.revoke_certificate(req.client_cert_sha)
        except Exception as e:
            logger.error("[API] Failed to persist revoked certificate in DB: %s", e)
        
        # Disconnect any peer associated with this certificate
        to_remove = []
        for name, peer in CROSS_CLOUD_GATEWAY.peers.items():
            if peer.get("cert_sha") == req.client_cert_sha:
                to_remove.append((name, peer.get("ws")))
                
        for name, ws in to_remove:
            CROSS_CLOUD_GATEWAY.peers.pop(name, None)
            if ws:
                try:
                    await ws.close(code=4003)
                except Exception:
                    pass
            revoked_count += 1

    if req.cloud_name:
        cloud = req.cloud_name.upper()
        peer = CROSS_CLOUD_GATEWAY.peers.pop(cloud, None)
        if peer:
            ws = peer.get("ws")
            if ws:
                try:
                    await ws.close(code=4003)
                except Exception:
                    pass
            revoked_count += 1

    return {
        "status": "success",
        "revoked_count": revoked_count,
        "total_revoked_certs": len(CROSS_CLOUD_GATEWAY.revoked_certs)
    }

@router.post("/v1/cross-cloud/reinstate")
async def reinstate_cross_cloud_cert(req: CrossCloudReinstateRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.cross_cloud_gateway import CROSS_CLOUD_GATEWAY
    CROSS_CLOUD_GATEWAY.revoked_certs.discard(req.client_cert_sha)
    try:
        CROSS_CLOUD_GATEWAY.audit_ledger.reinstate_certificate(req.client_cert_sha)
    except Exception as e:
        logger.error("[API] Failed to reinstate certificate in DB: %s", e)

    return {
        "status": "success",
        "client_cert_sha": req.client_cert_sha,
        "total_revoked_certs": len(CROSS_CLOUD_GATEWAY.revoked_certs)
    }

@router.get("/v1/cross-cloud/revoked")
async def get_revoked_certs(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.cross_cloud_gateway import CROSS_CLOUD_GATEWAY
    try:
        revoked_list = CROSS_CLOUD_GATEWAY.audit_ledger.get_revoked_certificates()
    except Exception as e:
        logger.error("[API] Failed to fetch revoked certificates from DB: %s", e)
        revoked_list = [{"cert_sha": sha, "revoked_at": None} for sha in CROSS_CLOUD_GATEWAY.revoked_certs]

    return {
        "status": "success",
        "revoked_certificates": revoked_list
    }

@router.websocket("/v1/cross-cloud/tunnel")
async def cross_cloud_tunnel_endpoint(websocket: WebSocket):
    params = websocket.query_params
    client_cert = params.get("client_cert")
    signature = params.get("signature")
    payload = params.get("payload")
    cloud_name = params.get("cloud_name", "").upper()
    
    from agent_workspace.core.cross_cloud_gateway import CROSS_CLOUD_GATEWAY

    if not CROSS_CLOUD_GATEWAY.validate_handshake(client_cert, signature, payload):
        await websocket.close(code=4003)
        return

    await websocket.accept()

    CROSS_CLOUD_GATEWAY.peers[cloud_name] = {
        "ws": websocket,
        "url": f"ws_client_{cloud_name}",
        "status": "connected",
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "simulated": False
    }

    logger.info("[CrossCloudGateway] Accepted WebSocket tunnel from %s", cloud_name)

    try:
        while True:
            data = await websocket.receive_text()
            packet = json.loads(data)
            await CROSS_CLOUD_GATEWAY.route_packet(packet)
    except WebSocketDisconnect:
        logger.info("[CrossCloudGateway] WebSocket tunnel disconnected from %s", cloud_name)
    except Exception as e:
        logger.error("[CrossCloudGateway] Error in WebSocket tunnel loop: %s", e)
    finally:
        CROSS_CLOUD_GATEWAY.peers.pop(cloud_name, None)
