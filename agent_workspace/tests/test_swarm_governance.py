import os
import sys
import json
import tempfile
import hashlib
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from core.audit_ledger import AuditLedger
from core.discussion_room import ProofOfConsensus, SwarmIDS
from core.governance import GovernanceManager, LATENCY_RULE_TEMPLATE, SAFETY_RULE_TEMPLATE
from core.prompt_composer import PromptComposer
from core.discussion_room import DiscussionRoom
from api import app

@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create standard .agent folders
        agent_dir = Path(temp_dir) / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "memory").mkdir(parents=True, exist_ok=True)
        (agent_dir / "prompts").mkdir(parents=True, exist_ok=True)
        yield temp_dir

@pytest.fixture
def api_client():
    return TestClient(app)

def test_governance_anomaly_scanning(temp_workspace):
    # Originally, no anomalies, so no proposals
    proposal = GovernanceManager.check_and_trigger_calibration(temp_workspace)
    assert proposal is None

    # 1. Record latency overrun in AuditLedger
    ledger = AuditLedger(temp_workspace)
    ledger.record_event("api_telemetry", {"duration_ms": 6000})

    # Trigger scan
    proposal = GovernanceManager.check_and_trigger_calibration(temp_workspace)
    assert proposal is not None
    assert proposal["rule_type"] == "latency_overrun"
    assert proposal["rule_text"] == LATENCY_RULE_TEMPLATE
    assert proposal["status"] == "proposed"

    # Trigger scan again, should not create a duplicate proposal
    dup_proposal = GovernanceManager.check_and_trigger_calibration(temp_workspace)
    assert dup_proposal is None

    # Now verify safety exception scan
    # Let's clear governance rules to allow a new proposal, or let's accept/reject it first
    # In this case, let's simulate a safety violation
    ledger.record_event("SOC2_VIOLATION", {"msg": "Unauthorized write attempted"})
    
    # Trigger scan
    proposal_safety = GovernanceManager.check_and_trigger_calibration(temp_workspace)
    assert proposal_safety is not None
    assert proposal_safety["rule_type"] == "safety_violation"
    assert proposal_safety["rule_text"] == SAFETY_RULE_TEMPLATE

def test_governance_cryptographic_voting_consensus(temp_workspace):
    ledger = AuditLedger(temp_workspace)
    ledger.record_event("safety_exception", {"msg": "invalid signature"})
    proposal = GovernanceManager.check_and_trigger_calibration(temp_workspace)
    assert proposal is not None
    proposal_id = proposal["id"]
    payload_hash = proposal["payload_hash"]

    # 1. Invalid signature should fail
    res = GovernanceManager.cast_vote(temp_workspace, proposal_id, "ceo", "approve", "bad-sig")
    assert res is False

    # 2. Valid signature from ceo (approve)
    sig_ceo = ProofOfConsensus.generate_member_signature("ceo", payload_hash)
    res = GovernanceManager.cast_vote(temp_workspace, proposal_id, "ceo", "approve", sig_ceo)
    assert res is True

    # Status should still be proposed (only 1 vote)
    proposals = GovernanceManager.get_all_proposals(temp_workspace)
    assert proposals[proposal_id]["status"] == "proposed"

    # 3. Valid signature from cto (approve)
    sig_cto = ProofOfConsensus.generate_member_signature("cto", payload_hash)
    res = GovernanceManager.cast_vote(temp_workspace, proposal_id, "cto", "approve", sig_cto)
    assert res is True
    assert GovernanceManager.get_all_proposals(temp_workspace)[proposal_id]["status"] == "proposed"

    # 4. Valid signature from dev (approve) -> Majority reached (3 out of 5)
    sig_dev = ProofOfConsensus.generate_member_signature("dev", payload_hash)
    res = GovernanceManager.cast_vote(temp_workspace, proposal_id, "dev", "approve", sig_dev)
    assert res is True
    
    # Status must be accepted and registered
    accepted_proposal = GovernanceManager.get_all_proposals(temp_workspace)[proposal_id]
    assert accepted_proposal["status"] == "accepted"
    assert "certificate" in accepted_proposal
    
    # Verify is_consensus_approved evaluates to True
    assert ProofOfConsensus.is_consensus_approved(temp_workspace, payload_hash) is True

    # Active rules list should contain the rule
    active_rules = GovernanceManager.get_active_rules(temp_workspace)
    assert SAFETY_RULE_TEMPLATE in active_rules

def test_prompt_composer_calibration_injection(temp_workspace):
    # Setup default role prompts
    prompt_id = "test_prompt"
    prompts_dir = Path(temp_workspace) / ".agent" / "prompts"
    prompt_file = prompts_dir / f"{prompt_id}.md"
    prompt_content = """---
id: test_prompt
version: 1.0.0
variables:
  - task_description
template: "Task: {{task_description}}"
---
"""
    prompt_file.write_text(prompt_content, encoding="utf-8")

    composer = PromptComposer(temp_workspace)

    # Initially, rules list is empty
    rendered = composer.build(prompt_id, {"task_description": "Fix bug"})
    assert "DYNAMIC GOVERNANCE CALIBRATION DIRECTIVES" not in rendered

    # Now register a consensus-accepted rule
    rule_text = LATENCY_RULE_TEMPLATE
    payload_hash = hashlib.sha256(rule_text.encode("utf-8")).hexdigest()
    
    # Accept a latency rule proposal
    data = {"proposals": {
        "prop_latency": {
            "id": "prop_latency",
            "rule_type": "latency_overrun",
            "rule_text": rule_text,
            "status": "accepted",
            "payload_hash": payload_hash,
            "votes": {},
            "signatures": {}
        }
    }}
    governance_file = Path(temp_workspace) / ".agent" / "memory" / "governance_rules.json"
    governance_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Generate certificate and register it
    cert = ProofOfConsensus.create_consensus_certificate(payload_hash, ["ceo", "cto", "dev"])
    ProofOfConsensus.register_consensus(temp_workspace, payload_hash, cert)

    # Render again - it must contain the rule
    rendered = composer.build(prompt_id, {"task_description": "Fix bug"})
    assert "DYNAMIC GOVERNANCE CALIBRATION DIRECTIVES" in rendered
    assert rule_text in rendered

@pytest.mark.asyncio
async def test_discussion_room_governance_vote(temp_workspace):
    proposal = {
        "id": "prop_test_vote",
        "rule_type": "latency_overrun",
        "rule_text": LATENCY_RULE_TEMPLATE,
        "payload_hash": hashlib.sha256(LATENCY_RULE_TEMPLATE.encode("utf-8")).hexdigest()
    }
    
    room = DiscussionRoom(temp_workspace)
    
    # Mock LLM complete method to vote APPROVE or REJECT
    mock_provider = MagicMock()
    mock_provider.complete = AsyncMock(return_value=("success", "APPROVE: Enforce efficiency."))
    
    with patch.object(room, "_resolve_agent_provider", return_value=(mock_provider, {}, "test-acc")):
        vote_result = await room.run_governance_vote(proposal)
        
        assert vote_result["proposal_id"] == "prop_test_vote"
        assert len(vote_result["votes"]) == 5
        assert all(v == "approve" for v in vote_result["votes"].values())
        assert len(vote_result["signatures"]) == 5

def test_api_governance_endpoints(api_client, temp_workspace):
    # Patch workspace inside api.py to point to our temp_workspace
    with patch("api.workspace", temp_workspace):
        # 1. GET rules endpoint
        res = api_client.get("/v1/swarm/governance/rules")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "proposals" in data
        assert "active_rules" in data

        # 2. Simulate setting up a proposal to vote on
        proposal_id = "api_prop"
        payload_hash = hashlib.sha256(LATENCY_RULE_TEMPLATE.encode("utf-8")).hexdigest()
        prop_data = {
            "proposals": {
                proposal_id: {
                    "id": proposal_id,
                    "rule_type": "latency_overrun",
                    "rule_text": LATENCY_RULE_TEMPLATE,
                    "status": "proposed",
                    "payload_hash": payload_hash,
                    "votes": {},
                    "signatures": {}
                }
            }
        }
        governance_file = Path(temp_workspace) / ".agent" / "memory" / "governance_rules.json"
        governance_file.write_text(json.dumps(prop_data, indent=2), encoding="utf-8")

        # 3. POST vote endpoint (invalid signature)
        res = api_client.post("/v1/swarm/governance/vote", json={
            "proposal_id": proposal_id,
            "role": "ceo",
            "vote": "approve",
            "signature": "bad-sig"
        })
        assert res.status_code == 400

        # 4. POST vote endpoint (valid signature)
        sig = ProofOfConsensus.generate_member_signature("ceo", payload_hash)
        res = api_client.post("/v1/swarm/governance/vote", json={
            "proposal_id": proposal_id,
            "role": "ceo",
            "vote": "approve",
            "signature": sig
        })
        assert res.status_code == 200
        assert res.json()["status"] == "success"
