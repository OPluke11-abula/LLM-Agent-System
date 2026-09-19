"""Capability-Aware Mesh Factory Workload Dispatcher (Phase 101).

Maps refactoring DAG task waves to heterogeneous Federated Mesh nodes based on peer
advertised capabilities (Reasoning Engine, Sandbox Mutation, Test Runner).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence, Union

from agent_workspace.core.factory.models import (
    FactoryDispatchAssignment,
    FactoryDispatchPlan,
    RefactoringTaskDAG,
    RefactoringTaskNode,
    RefactoringTaskType,
)
from agent_workspace.core.federated_mesh import PeerCapability

logger = logging.getLogger("MeshDispatcher")


class MeshFactoryDispatcher:
    """Dispatches refactoring task waves across heterogeneous federated mesh nodes."""

    def __init__(
        self,
        registered_peers: Optional[Dict[str, List[Union[PeerCapability, str]]]] = None,
    ) -> None:
        # Default local/mock node capabilities if none provided
        self.peers: Dict[str, List[str]] = {}
        if registered_peers:
            for pid, caps in registered_peers.items():
                self.peers[pid] = [c.value if isinstance(c, PeerCapability) else str(c) for c in caps]
        else:
            self.peers = {
                "node-cloud-reasoner": [PeerCapability.REASONING_ENGINE.value],
                "node-edge-mutation-01": [PeerCapability.SANDBOX_MUTATION.value],
                "node-edge-mutation-02": [PeerCapability.SANDBOX_MUTATION.value],
                "node-ci-test-runner": [PeerCapability.TEST_RUNNER.value],
            }

        self.dispatch_history: List[FactoryDispatchPlan] = []

    def register_peer(self, peer_id: str, capabilities: List[Union[PeerCapability, str]]) -> None:
        """Registers or updates a mesh peer and its advertised capabilities."""
        self.peers[peer_id] = [c.value if isinstance(c, PeerCapability) else str(c) for c in capabilities]

    def unregister_peer(self, peer_id: str) -> None:
        """Removes a mesh peer upon disconnect or attestation revocation."""
        self.peers.pop(peer_id, None)

    def _determine_required_capability(self, task: RefactoringTaskNode) -> PeerCapability:
        """Determines the primary hardware/LLM capability needed for the task."""
        if task.task_type in (RefactoringTaskType.MODULARIZE, RefactoringTaskType.DECOUPLING):
            return PeerCapability.REASONING_ENGINE
        elif task.task_type == RefactoringTaskType.TEST_EXPANSION:
            return PeerCapability.TEST_RUNNER
        else:
            return PeerCapability.SANDBOX_MUTATION

    def _find_best_peer(self, required_cap: PeerCapability, wave_assigned_peers: Sequence[str]) -> str:
        """Finds the least-loaded peer matching the required capability."""
        cap_val = required_cap.value

        # First priority: matching capability not yet assigned in this wave
        available = [
            pid for pid, caps in self.peers.items()
            if cap_val in caps and pid not in wave_assigned_peers
        ]
        if available:
            return available[0]

        # Second priority: any matching capability peer
        matching = [pid for pid, caps in self.peers.items() if cap_val in caps]
        if matching:
            return matching[0]

        # Fallback: any available peer in the mesh
        if self.peers:
            return list(self.peers.keys())[0]

        return "node-fallback-local"

    def create_dispatch_plan(self, dag: RefactoringTaskDAG) -> FactoryDispatchPlan:
        """Generates an end-to-end execution dispatch plan for the refactoring DAG."""
        waves = dag.get_parallel_waves()
        plan = FactoryDispatchPlan(
            dag_id=dag.dag_id,
            total_waves=len(waves),
            wave_breakdown=[],
        )

        for wave_idx, wave in enumerate(waves, start=1):
            wave_task_ids: List[str] = []
            assigned_in_wave: List[str] = []

            for task in wave:
                req_cap = self._determine_required_capability(task)
                target_peer = self._find_best_peer(req_cap, assigned_in_wave)
                assigned_in_wave.append(target_peer)

                assignment = FactoryDispatchAssignment(
                    task_id=task.node_id,
                    task_title=task.title,
                    assigned_peer_id=target_peer,
                    required_capability=req_cap.value,
                    status="SCHEDULED",
                )
                plan.assignments.append(assignment)
                wave_task_ids.append(task.node_id)

            plan.wave_breakdown.append(wave_task_ids)

        self.dispatch_history.append(plan)
        logger.info(
            "[MeshDispatcher] Created dispatch plan %s for DAG %s (%d tasks across %d waves)",
            plan.plan_id,
            dag.dag_id,
            len(dag.nodes),
            plan.total_waves,
        )
        return plan
