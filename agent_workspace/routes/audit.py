import os
import sys
import logging
from fastapi import APIRouter, Depends, HTTPException

from agent_workspace.routes.dependencies import get_tenant_context, workspace, get_workspace
from agent_workspace.routes.schemas import AuditVerifyProofRequest

logger = logging.getLogger("api.audit")

router = APIRouter()

@router.get("/v1/audit/logs")
async def get_audit_logs(event_type: str | None = None, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.audit_ledger import AuditLedger
    ledger = AuditLedger(get_workspace())
    logs = ledger.get_logs(event_type, tenant_id=tenant_id)
    return {"status": "success", "logs": logs}

@router.get("/v1/audit/verify")
async def verify_audit_chain(tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.audit_ledger import AuditLedger
    ledger = AuditLedger(get_workspace())
    verification = ledger.verify_chain_integrity()
    return {"status": "success", **verification}

@router.get("/v1/audit/status")
async def get_audit_status(tenant_id: str = Depends(get_tenant_context)):
    import agent_workspace.api as api_mod
    from agent_workspace.core.audit_ledger import AuditLedger
    ledger = AuditLedger(get_workspace())
    verification = ledger.verify_chain_integrity()
    logs = ledger.get_logs(tenant_id=tenant_id)
    
    peers = {}
    if api_mod._audit_daemon:
        peers = api_mod._audit_daemon.peer_states
        
    return {
        "status": "success",
        "valid": verification.get("valid", False),
        "tampered_id": verification.get("tampered_id"),
        "merkle_root": verification.get("merkle_root", "0" * 64),
        "event_count": len(logs),
        "peers": peers
    }

@router.post("/v1/audit/sync")
async def trigger_audit_sync(tenant_id: str = Depends(get_tenant_context)):
    import agent_workspace.api as api_mod
    if api_mod._audit_daemon:
        await api_mod._audit_daemon.trigger_manual_sync()
        peers_queried = len(api_mod._audit_daemon.peer_states)
    else:
        peers_queried = 0
    return {
        "status": "success",
        "message": "Consensus audit triggered",
        "peers_queried": peers_queried
    }

@router.get("/v1/audit/proof/{event_id}")
async def get_audit_proof(event_id: int, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.audit_ledger import AuditLedger
    ledger = AuditLedger(get_workspace())
    proof_data = ledger.generate_merkle_proof(event_id)
    if not proof_data:
        raise HTTPException(status_code=404, detail="Audit event or proof not found")

    zk_proof = ledger.generate_zk_proof(event_id)

    return {
        "status": "success",
        "event_id": event_id,
        "event_hash": proof_data["event_hash"],
        "merkle_proof": proof_data["proof"],
        "zk_proof": zk_proof,
        "zk_verification_key": "zk-audit-v1-key"
    }

@router.post("/v1/audit/verify-proof")
async def verify_audit_proof(req: AuditVerifyProofRequest, tenant_id: str = Depends(get_tenant_context)):
    from agent_workspace.core.audit_ledger import AuditLedger
    is_valid = AuditLedger.verify_merkle_proof(req.event_hash, req.proof, req.root_hash)
    return {
        "status": "success",
        "valid": is_valid
    }
