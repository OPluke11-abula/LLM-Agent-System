"""Phase 107 Test Suite: Advanced Multimodal Swarm Mesh & P2P Stress Verification.

Validates:
1. PeerCapability.MULTIMODAL_PERCEPTION registration and discovery.
2. MultimodalVerificationReceipt payload integrity and Merkle proof generation.
3. MeshFactoryDispatcher capability-aware routing of visual and diagram tasks.
4. FederatedMeshCoordinator multimodal task delegation and cryptographic attestation.
"""

from __future__ import annotations

import hashlib
import pytest
from pathlib import Path

from agent_workspace.core.factory.mesh_dispatcher import MeshFactoryDispatcher
from agent_workspace.core.factory.models import (
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)
from agent_workspace.core.federated_mesh import (
    AttestationStatus,
    FederatedMeshCoordinator,
    FederatedPeerProfile,
    MultimodalVerificationReceipt,
    PeerCapability,
)


def test_peer_capability_multimodal_enum():
    """Validates that MULTIMODAL_PERCEPTION is recognized as a first-class mesh capability."""
    assert hasattr(PeerCapability, "MULTIMODAL_PERCEPTION")
    assert PeerCapability.MULTIMODAL_PERCEPTION.value == "MULTIMODAL_PERCEPTION"
    assert PeerCapability.MULTIMODAL_PERCEPTION != PeerCapability.REASONING_ENGINE


def test_multimodal_verification_receipt():
    """Validates receipt creation and Merkle cryptographic binding."""
    raw_svg = b"<svg><rect width='100' height='100' fill='cyan'/></svg>"
    payload_hash = hashlib.sha256(raw_svg).hexdigest()

    receipt = MultimodalVerificationReceipt(
        task_id="task-visual-01",
        media_type="image/svg+xml",
        payload_hash=payload_hash,
        visual_diff_detected=False,
        confidence_score=0.98,
        findings=["SVG vector structure aligns with DESIGN.md color tokens."],
        merkle_root=hashlib.sha256(payload_hash.encode("utf-8") + b"task-visual-01").hexdigest(),
        verified_by_node_id="node-multimodal-test",
    )

    assert receipt.task_id == "task-visual-01"
    assert receipt.payload_hash == payload_hash
    assert not receipt.visual_diff_detected
    assert receipt.confidence_score == 0.98
    assert len(receipt.merkle_root) == 64
    assert receipt.verified_by_node_id == "node-multimodal-test"


def test_mesh_dispatcher_routes_visual_tasks():
    """Validates that RefactoringTaskType.VISUAL_VERIFICATION routes to MULTIMODAL_PERCEPTION peers."""
    dispatcher = MeshFactoryDispatcher()

    # Verify default registration contains node-multimodal-verifier
    assert "node-multimodal-verifier" in dispatcher.peers
    assert PeerCapability.MULTIMODAL_PERCEPTION.value in dispatcher.peers["node-multimodal-verifier"]

    # Create DAG with mixed tasks: 1 code modularize, 1 test, 1 visual verification
    t1 = RefactoringTaskNode(
        node_id="task-mod-01",
        title="Modularize monolithic component",
        task_type=RefactoringTaskType.MODULARIZE,
        target_files=["viewer/src/components/GiantView.tsx"],
        mutable_scope=["viewer/src/components/GiantView.tsx"],
    )
    t2 = RefactoringTaskNode(
        node_id="task-test-01",
        title="Expand test coverage",
        task_type=RefactoringTaskType.TEST_EXPANSION,
        target_files=["tests/test_giant.py"],
        mutable_scope=["tests/test_giant.py"],
    )
    t3 = RefactoringTaskNode(
        node_id="task-vis-01",
        title="Verify UI layout tokens against DESIGN.md",
        task_type=RefactoringTaskType.VISUAL_VERIFICATION,
        target_files=["viewer/src/components/Companion.tsx"],
        mutable_scope=[],
    )

    dag = RefactoringTaskDAG(name="Multimodal-Test-DAG")
    dag.add_node(t1)
    dag.add_node(t2)
    dag.add_node(t3)


    plan = dispatcher.create_dispatch_plan(dag)
    assert plan.total_waves >= 1

    # Find assignment for t3
    assigned_peers = {a.task_id: a.assigned_peer_id for a in plan.assignments}
    assert assigned_peers["task-vis-01"] == "node-multimodal-verifier"
    assert assigned_peers["task-mod-01"] == "node-cloud-reasoner"
    assert assigned_peers["task-test-01"] == "node-ci-test-runner"



@pytest.mark.asyncio
async def test_federated_mesh_multimodal_delegation():
    """Validates end-to-end multimodal verification delegation in FederatedMeshCoordinator."""
    coordinator = FederatedMeshCoordinator(
        node_id="coordinator-root",
        role="architect",
        capabilities=[PeerCapability.COCKPIT_LEADER],
    )

    # Register a multimodal perception peer
    multimodal_peer = FederatedPeerProfile(
        node_id="node-vision-worker-01",
        role="ui_ux",
        host="127.0.0.1",
        port=9010,
        capabilities=[PeerCapability.MULTIMODAL_PERCEPTION],
        status="connected",
        latency_ms=12.0,
        load_score=0.1,
        attestation_status=AttestationStatus.VERIFIED,
    )
    coordinator.register_peer(multimodal_peer)

    # Verify best peer selection
    best_peer = coordinator.select_best_peer(PeerCapability.MULTIMODAL_PERCEPTION)
    assert best_peer is not None
    assert best_peer.node_id == "node-vision-worker-01"

    # Delegate multimodal check
    fake_screenshot_bytes = b"PNG_MOCK_IMAGE_DATA_0123456789"
    result = await coordinator.delegate_multimodal_verification(
        task_id="task-companion-snap",
        media_type="image/png",
        payload_bytes=fake_screenshot_bytes,
        description="Verify Ambient Companion 9-step stepper alignment",
    )

    assert result is not None
    assert result["verified"] is True
    assert result["media_type"] == "image/png"
    assert result["confidence_score"] >= 0.95
    assert result["verified_by_node_id"] == "node-vision-worker-01"
    assert len(result["merkle_root"]) == 64
    assert len(result["findings"]) >= 1
