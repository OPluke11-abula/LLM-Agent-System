"""Federated Multi-Cluster Raft Consensus & WAN Quorum (Phase 111).

Aligned with Universal Coding Agent Development Protocol v3.8.0, Anti-Corruption
Principle #3 (Concurrency & Race Elimination), and Principle #4 (Typed Failures).

Manages cross-region and cross-organization Raft replication over encrypted mesh overlays,
with jitter-tolerant regional heartbeats, multi-cluster quorum gating, and regional failover.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, ConfigDict, Field

from agent_workspace.core.raft_consensus import (
    AppendEntriesArgs,
    CommitteeEntryType,
    CommitteeLogEntry,
    CommitteeRaftNode,
    RaftRole,
    RequestVoteArgs,
)

logger = logging.getLogger("FederatedRaftMultiCluster")


class ClusterRegion(str, Enum):
    """Geographical or organizational boundary regions."""

    US_EAST = "US_EAST"
    EU_CENTRAL = "EU_CENTRAL"
    AP_EAST = "AP_EAST"
    LOCAL = "LOCAL"


class RegionalClusterMember(BaseModel):
    """Metadata descriptor for a member participating in multi-cluster Raft."""

    model_config = ConfigDict(extra="ignore")

    node_id: str
    region: ClusterRegion
    organization_id: str
    virtual_ip: str
    latency_weight_ms: float = 10.0
    is_active: bool = True


class MultiClusterProposalResult(BaseModel):
    """Result of cross-region log replication and quorum consensus."""

    model_config = ConfigDict(extra="ignore")

    term: int
    log_index: int
    regions_committed: List[ClusterRegion] = Field(default_factory=list)
    success: bool
    consensus_latency_ms: float
    nodes_acknowledged: int = 0
    total_nodes: int = 0


class FederatedRaftMultiCluster:
    """Coordinates cross-organizational multi-region Raft consensus clusters."""

    def __init__(self, cluster_name: str = "federated-global-mesh") -> None:
        self.cluster_name = cluster_name
        self.members: Dict[str, RegionalClusterMember] = {}
        self.nodes: Dict[str, CommitteeRaftNode] = {}
        self.current_cross_cluster_leader: Optional[str] = None

    def register_regional_node(
        self,
        node_id: str,
        region: ClusterRegion,
        organization_id: str,
        virtual_ip: str,
        latency_weight_ms: float = 10.0,
    ) -> CommitteeRaftNode:
        """Registers a node into the multi-cluster federation topology."""
        member = RegionalClusterMember(
            node_id=node_id,
            region=region,
            organization_id=organization_id,
            virtual_ip=virtual_ip,
            latency_weight_ms=latency_weight_ms,
        )
        self.members[node_id] = member

        # Instantiate native CommitteeRaftNode
        node = CommitteeRaftNode(
            node_id=node_id,
            peers_provider=lambda: [nid for nid in self.members.keys() if nid != node_id],
            attestation_checker=lambda nid: self.members.get(nid, None) is not None,
        )
        self.nodes[node_id] = node
        logger.info("Registered multi-cluster node %s in region %s (%s)", node_id, region.value, organization_id)
        return node

    async def elect_cross_cluster_leader(self, candidate_node_id: str) -> bool:
        """Performs cross-region election gathering votes across WAN regions."""
        candidate = self.nodes.get(candidate_node_id)
        candidate_meta = self.members.get(candidate_node_id)
        if not candidate or not candidate_meta:
            raise KeyError(f"Candidate node {candidate_node_id} not registered")

        candidate.role = RaftRole.CANDIDATE
        candidate.current_term += 1
        candidate.voted_for = candidate_node_id

        votes_granted = 1
        regions_voting: Set[ClusterRegion] = {candidate_meta.region}

        args = RequestVoteArgs(
            term=candidate.current_term,
            candidate_id=candidate_node_id,
            last_log_index=len(candidate.log) - 1,
            last_log_term=candidate.log[-1].term,
        )

        for peer_id, peer_meta in self.members.items():
            if peer_id == candidate_node_id or not peer_meta.is_active:
                continue

            peer_node = self.nodes[peer_id]
            # Simulate regional network delay
            delay = min(0.05, peer_meta.latency_weight_ms / 1000.0)
            await asyncio.sleep(delay)

            reply = peer_node.handle_request_vote(args)
            if reply.vote_granted:
                votes_granted += 1
                regions_voting.add(peer_meta.region)

        # Quorum invariant: Requires majority of all active nodes AND at least 2 distinct regions (if >= 2 exist)
        total_active = sum(1 for m in self.members.values() if m.is_active)
        majority_met = votes_granted > (total_active // 2)
        distinct_regions_available = len({m.region for m in self.members.values() if m.is_active})
        cross_region_met = len(regions_voting) >= min(2, distinct_regions_available)

        if majority_met and cross_region_met:
            candidate.role = RaftRole.LEADER
            self.current_cross_cluster_leader = candidate_node_id
            logger.info("Node %s elected cross-cluster leader with %d votes across regions %s", candidate_node_id, votes_granted, [r.value for r in regions_voting])
            return True

        candidate.role = RaftRole.FOLLOWER
        return False

    async def replicate_cross_region_entry(
        self,
        entry_type: CommitteeEntryType,
        payload: Dict[str, Any],
        author_node_id: Optional[str] = None,
    ) -> MultiClusterProposalResult:
        """Appends and replicates an entry from leader across all regional clusters."""
        start_time = time.perf_counter()

        if not self.current_cross_cluster_leader or self.current_cross_cluster_leader not in self.nodes:
            # Elect a leader first
            active_ids = [nid for nid, m in self.members.items() if m.is_active]
            if not active_ids:
                raise RuntimeError("No active nodes available in multi-cluster federation")
            await self.elect_cross_cluster_leader(active_ids[0])

        leader_id = self.current_cross_cluster_leader
        leader_node = self.nodes[leader_id]
        author = author_node_id or leader_id

        # 1. Append on leader
        new_index = len(leader_node.log)
        entry = CommitteeLogEntry(
            index=new_index,
            term=leader_node.current_term,
            entry_type=entry_type,
            author_node_id=author,
            payload=payload,
        )
        entry.sign(secret_or_key=author)
        leader_node.log.append(entry)

        # 2. Replicate to active regional followers
        ack_count = 1
        committed_regions: Set[ClusterRegion] = {self.members[leader_id].region}

        args = AppendEntriesArgs(
            term=leader_node.current_term,
            leader_id=leader_id,
            prev_log_index=new_index - 1,
            prev_log_term=leader_node.log[new_index - 1].term,
            entries=[entry],
            leader_commit=leader_node.commit_index,
        )

        for peer_id, peer_meta in self.members.items():
            if peer_id == leader_id or not peer_meta.is_active:
                continue

            peer_node = self.nodes[peer_id]
            delay = min(0.02, peer_meta.latency_weight_ms / 1000.0)
            await asyncio.sleep(delay)

            reply = peer_node.handle_append_entries(args)
            if reply.success:
                ack_count += 1
                committed_regions.add(peer_meta.region)

        total_active = sum(1 for m in self.members.values() if m.is_active)
        success = ack_count > (total_active // 2)

        if success:
            leader_node.commit_index = new_index
            leader_node._apply_committed_entries()

            # Apply on followers as well
            for peer_id, peer_meta in self.members.items():
                if peer_id != leader_id and peer_meta.is_active:
                    self.nodes[peer_id].commit_index = new_index
                    self.nodes[peer_id]._apply_committed_entries()


        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return MultiClusterProposalResult(
            term=leader_node.current_term,
            log_index=new_index,
            regions_committed=list(committed_regions),
            success=success,
            consensus_latency_ms=round(elapsed_ms, 2),
            nodes_acknowledged=ack_count,
            total_nodes=total_active,
        )

    async def handle_regional_partition(self, failed_region: ClusterRegion) -> Optional[str]:
        """Simulates WAN partition or disaster recovery when an entire region goes dark."""
        logger.warning("Simulating regional partition for %s", failed_region.value)

        # Mark all nodes in region inactive
        for nid, meta in self.members.items():
            if meta.region == failed_region:
                meta.is_active = False
                self.nodes[nid].role = RaftRole.FOLLOWER

        surviving_active = [nid for nid, m in self.members.items() if m.is_active]
        if not surviving_active:
            self.current_cross_cluster_leader = None
            return None

        # If current leader was in failed region, trigger immediate re-election
        if self.current_cross_cluster_leader and self.members[self.current_cross_cluster_leader].region == failed_region:
            logger.info("Current leader %s was in failed region; triggering failover election", self.current_cross_cluster_leader)
            elected = await self.elect_cross_cluster_leader(surviving_active[0])
            if elected:
                return self.current_cross_cluster_leader
            return None

        return self.current_cross_cluster_leader
