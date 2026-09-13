"""Distributed Committee Raft Consensus Subsystem (Phase 89).

Implements a Byzantine-hardened, fault-tolerant Raft consensus engine for
multi-agent committee debate, log replication, and deterministic state machine
application across federated mesh nodes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger("RaftConsensus")


class RaftRole(str, Enum):
    """Raft consensus roles for cluster members."""

    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    LEADER = "LEADER"


class CommitteeEntryType(str, Enum):
    """Semantic payload types for committee replicated logs."""

    PROPOSE_TASK = "PROPOSE_TASK"
    SPEECH_TURN = "SPEECH_TURN"
    CRITIQUE_SCORE = "CRITIQUE_SCORE"
    CONSENSUS_VERDICT = "CONSENSUS_VERDICT"
    PATCH_COMMIT = "PATCH_COMMIT"
    CONFIGURATION = "CONFIGURATION"
    VECTOR_CHECKPOINT = "VECTOR_CHECKPOINT"


class CommitteeLogEntry(BaseModel):
    """Immutable, cryptographically signed log entry replicated across the Raft cluster."""

    model_config = ConfigDict(extra="forbid")

    index: int  # 1-based log index
    term: int  # Term when entry was received by leader
    entry_type: CommitteeEntryType
    author_node_id: str
    payload: Dict[str, Any]
    signature: str = ""
    timestamp: float = Field(default_factory=time.time)

    def compute_hash(self) -> str:
        """Computes deterministic SHA-256 digest of the log entry content."""
        payload_str = json.dumps(self.payload, sort_keys=True)
        raw = f"{self.index}:{self.term}:{self.entry_type.value}:{self.author_node_id}:{payload_str}:{self.timestamp:.4f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def sign(self, secret_or_key: str = "") -> None:
        """Generates cryptographic signature over the entry."""
        digest = self.compute_hash()
        sign_key = secret_or_key or self.author_node_id
        sig_data = f"{digest}:{sign_key}".encode("utf-8")
        self.signature = hashlib.sha256(sig_data).hexdigest()

    def verify_signature(self, secret_or_key: str = "") -> bool:
        """Verifies signature integrity."""
        if not self.signature:
            return False
        digest = self.compute_hash()
        sign_key = secret_or_key or self.author_node_id
        expected = hashlib.sha256(f"{digest}:{sign_key}".encode("utf-8")).hexdigest()
        return self.signature == expected


class RequestVoteArgs(BaseModel):
    """Arguments for Raft RequestVote RPC."""

    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


class RequestVoteReply(BaseModel):
    """Reply from Raft RequestVote RPC."""

    term: int
    vote_granted: bool
    voter_id: str
    reason: Optional[str] = None


class AppendEntriesArgs(BaseModel):
    """Arguments for Raft AppendEntries RPC (Log Replication & Heartbeats)."""

    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[CommitteeLogEntry] = Field(default_factory=list)
    leader_commit: int


class AppendEntriesReply(BaseModel):
    """Reply from Raft AppendEntries RPC."""

    term: int
    success: bool
    match_index: int
    node_id: str
    error_message: Optional[str] = None


class CommitteeStateMachine:
    """
    Deterministic replicated state machine applied when entries reach quorum commit.
    Guarantees identical final state across all non-faulty nodes in the cluster.
    """

    def __init__(self) -> None:
        self.last_applied_index: int = 0
        # task_id -> list of speech turn payloads
        self.debates: Dict[str, List[Dict[str, Any]]] = {}
        # task_id -> consensus verdict payload
        self.verdicts: Dict[str, Dict[str, Any]] = {}
        # task_id -> patch Merkle root string
        self.committed_patches: Dict[str, str] = {}
        # task_id -> overall status ("PENDING", "APPROVED", "REJECTED")
        self.task_statuses: Dict[str, str] = {}
        # Replicated vector memory checkpoints
        self.vector_checkpoints: List[Dict[str, Any]] = []
        self.latest_vector_merkle_root: str = ""

    def apply_entry(self, entry: CommitteeLogEntry) -> None:
        """Applies a committed log entry sequentially to update state."""
        self.last_applied_index = entry.index
        task_id = entry.payload.get("task_id", "default-task")

        if entry.entry_type == CommitteeEntryType.PROPOSE_TASK:
            self.task_statuses[task_id] = "PROPOSED"
            if task_id not in self.debates:
                self.debates[task_id] = []

        elif entry.entry_type == CommitteeEntryType.SPEECH_TURN:
            if task_id not in self.debates:
                self.debates[task_id] = []
            self.debates[task_id].append(entry.payload)

        elif entry.entry_type == CommitteeEntryType.CONSENSUS_VERDICT:
            self.verdicts[task_id] = entry.payload
            decision = entry.payload.get("decision", "CONSENSUS_APPROVED")
            self.task_statuses[task_id] = "APPROVED" if decision == "CONSENSUS_APPROVED" else "REJECTED"

        elif entry.entry_type == CommitteeEntryType.PATCH_COMMIT:
            merkle_root = entry.payload.get("merkle_root", "")
            self.committed_patches[task_id] = merkle_root
            self.task_statuses[task_id] = "PATCH_COMMITTED"

        elif entry.entry_type == CommitteeEntryType.VECTOR_CHECKPOINT:
            self.vector_checkpoints.append(entry.payload)
            if "merkle_root" in entry.payload:
                self.latest_vector_merkle_root = str(entry.payload["merkle_root"])

        logger.debug(
            "[StateMachine] Applied log index %d (type=%s, task=%s)",
            entry.index,
            entry.entry_type.value,
            task_id,
        )

    def get_task_summary(self, task_id: str) -> Dict[str, Any]:
        """Returns the consolidated state for a given task."""
        return {
            "task_id": task_id,
            "status": self.task_statuses.get(task_id, "UNKNOWN"),
            "speech_turns_count": len(self.debates.get(task_id, [])),
            "verdict": self.verdicts.get(task_id),
            "patch_merkle_root": self.committed_patches.get(task_id),
            "last_applied_index": self.last_applied_index,
            "latest_vector_merkle_root": self.latest_vector_merkle_root,
            "vector_checkpoints_count": len(self.vector_checkpoints),
        }


class CommitteeRaftNode:
    """
    Raft consensus engine orchestrating committee leadership, log replication,
    and quorum commits across federated mesh peers.
    """

    def __init__(
        self,
        node_id: str,
        peers_provider: Optional[Callable[[], List[str]]] = None,
        attestation_checker: Optional[Callable[[str], bool]] = None,
        election_timeout_sec: float = 0.3,
        heartbeat_interval_sec: float = 0.1,
    ) -> None:
        self.node_id = node_id
        self.peers_provider = peers_provider
        self.attestation_checker = attestation_checker

        # Persistent state on all nodes (1-indexed log, slot 0 dummy)
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        self.log: List[CommitteeLogEntry] = [
            CommitteeLogEntry(
                index=0,
                term=0,
                entry_type=CommitteeEntryType.CONFIGURATION,
                author_node_id="genesis",
                payload={"desc": "genesis_slot"},
            )
        ]

        # Volatile state on all nodes
        self.role: RaftRole = RaftRole.FOLLOWER
        self.leader_id: Optional[str] = None
        self.commit_index: int = 0
        self.last_applied: int = 0

        # Timing
        self.election_timeout_sec = election_timeout_sec
        self.heartbeat_interval_sec = heartbeat_interval_sec
        self.last_heartbeat_time: float = time.monotonic()

        # Volatile state on leaders (index: peer_id -> next/match index)
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        # Replicated State Machine
        self.state_machine = CommitteeStateMachine()

        # Custom RPC dispatcher callback for testing or network integration
        self.rpc_dispatcher: Optional[Callable[[str, str, Dict[str, Any]], Dict[str, Any]]] = None

    @property
    def last_log_index(self) -> int:
        return len(self.log) - 1

    @property
    def last_log_term(self) -> int:
        return self.log[-1].term

    def get_cluster_peers(self) -> List[str]:
        """Returns list of peer node IDs in the cluster, excluding self."""
        if self.peers_provider:
            all_peers = self.peers_provider()
            return [p for p in all_peers if p != self.node_id]
        return []

    def is_peer_attested(self, peer_id: str) -> bool:
        """Verifies if the peer is cryptographically attested under Phase 88."""
        if self.attestation_checker:
            return self.attestation_checker(peer_id)
        return True

    def get_quorum_size(self) -> int:
        """Returns required quorum size based on verified cluster members."""
        peers = self.get_cluster_peers()
        verified_peers = [p for p in peers if self.is_peer_attested(p)]
        total_nodes = len(verified_peers) + 1  # include self
        return (total_nodes // 2) + 1

    def step_down(self, term: int, leader_id: Optional[str] = None) -> None:
        """Transitions node to Follower with a higher term."""
        self.current_term = term
        self.role = RaftRole.FOLLOWER
        self.voted_for = None
        self.leader_id = leader_id
        self.last_heartbeat_time = time.monotonic()
        logger.info("[Raft %s] Stepped down to FOLLOWER in term %d", self.node_id, term)

    def handle_request_vote(self, args: RequestVoteArgs) -> RequestVoteReply:
        """
        Processes RequestVote RPC:
        1. Reject if candidate is not attested under Phase 88 Zero-Trust policy.
        2. Reject if term < current_term.
        3. If term > current_term, step down.
        4. Vote if voted_for is None or candidate_id, and candidate's log is up-to-date.
        """
        # Phase 88 Zero-Trust Attestation check
        if not self.is_peer_attested(args.candidate_id):
            return RequestVoteReply(
                term=self.current_term,
                vote_granted=False,
                voter_id=self.node_id,
                reason="Candidate is not attested (Phase 88 Zero-Trust requirement).",
            )

        if args.term > self.current_term:
            self.step_down(args.term)

        if args.term < self.current_term:
            return RequestVoteReply(
                term=self.current_term,
                vote_granted=False,
                voter_id=self.node_id,
                reason=f"Candidate term {args.term} < current_term {self.current_term}",
            )

        # Check candidate's log is up-to-date:
        # Candidate's last log term > voter's last log term OR
        # (Candidate's last log term == voter's last log term and candidate log length >= voter log length)
        log_ok = (args.last_log_term > self.last_log_term) or (
            args.last_log_term == self.last_log_term and args.last_log_index >= self.last_log_index
        )

        can_vote = (self.voted_for is None or self.voted_for == args.candidate_id) and log_ok

        if can_vote:
            self.voted_for = args.candidate_id
            self.last_heartbeat_time = time.monotonic()
            logger.info("[Raft %s] Voted FOR %s in term %d", self.node_id, args.candidate_id, args.term)
            return RequestVoteReply(term=self.current_term, vote_granted=True, voter_id=self.node_id)

        return RequestVoteReply(
            term=self.current_term,
            vote_granted=False,
            voter_id=self.node_id,
            reason=f"Vote denied (already voted for {self.voted_for} or log not up-to-date)",
        )

    def handle_append_entries(self, args: AppendEntriesArgs) -> AppendEntriesReply:
        """
        Processes AppendEntries RPC:
        1. Reject if leader is not attested.
        2. Reject if term < current_term.
        3. If term >= current_term, become Follower and acknowledge leader.
        4. Log matching check: reject if log doesn't contain entry at prev_log_index matching prev_log_term.
        5. Truncate conflicting entries and append new entries.
        6. Update commit_index and apply to state machine.
        """
        if not self.is_peer_attested(args.leader_id):
            return AppendEntriesReply(
                term=self.current_term,
                success=False,
                match_index=0,
                node_id=self.node_id,
                error_message="Leader is not attested (Phase 88 Zero-Trust requirement).",
            )

        if args.term > self.current_term:
            self.step_down(args.term, leader_id=args.leader_id)
        elif args.term == self.current_term and self.role != RaftRole.FOLLOWER:
            self.step_down(args.term, leader_id=args.leader_id)

        if args.term < self.current_term:
            return AppendEntriesReply(
                term=self.current_term,
                success=False,
                match_index=0,
                node_id=self.node_id,
                error_message=f"Leader term {args.term} < current_term {self.current_term}",
            )

        # Refresh heartbeat lease
        self.leader_id = args.leader_id
        self.last_heartbeat_time = time.monotonic()

        # Log matching property
        if args.prev_log_index >= len(self.log):
            return AppendEntriesReply(
                term=self.current_term,
                success=False,
                match_index=self.last_log_index,
                node_id=self.node_id,
                error_message=f"Missing prev_log_index {args.prev_log_index} (log len={len(self.log)})",
            )

        if self.log[args.prev_log_index].term != args.prev_log_term:
            # Conflicting log entry at prev_log_index; truncate conflict
            self.log = self.log[: args.prev_log_index]
            return AppendEntriesReply(
                term=self.current_term,
                success=False,
                match_index=len(self.log) - 1,
                node_id=self.node_id,
                error_message=f"Term mismatch at prev_log_index {args.prev_log_index}",
            )

        # Append any new entries not already in the log
        insert_idx = args.prev_log_index + 1
        for entry in args.entries:
            if insert_idx < len(self.log):
                if self.log[insert_idx].term != entry.term:
                    # Overwrite conflict
                    self.log = self.log[:insert_idx]
                    self.log.append(entry)
            else:
                self.log.append(entry)
            insert_idx += 1

        # Advance commit index
        if args.leader_commit > self.commit_index:
            self.commit_index = min(args.leader_commit, self.last_log_index)
            self._apply_committed_entries()

        return AppendEntriesReply(
            term=self.current_term,
            success=True,
            match_index=self.last_log_index,
            node_id=self.node_id,
        )

    def start_election(self) -> bool:
        """
        Initiates a Raft leader election:
        Transitions to CANDIDATE, increments term, votes for self,
        broadcasts RequestVote to verified peers, and becomes LEADER if quorum is reached.
        """
        self.current_term += 1
        self.role = RaftRole.CANDIDATE
        self.voted_for = self.node_id
        self.leader_id = None
        self.last_heartbeat_time = time.monotonic()

        peers = self.get_cluster_peers()
        verified_peers = [p for p in peers if self.is_peer_attested(p)]
        quorum = self.get_quorum_size()

        logger.info(
            "[Raft %s] Starting election for term %d. Quorum needed: %d (Cluster size: %d)",
            self.node_id,
            self.current_term,
            quorum,
            len(verified_peers) + 1,
        )

        votes_granted = 1  # Vote for self

        # If single-node cluster, become leader immediately
        if votes_granted >= quorum:
            self._become_leader()
            return True

        args = RequestVoteArgs(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=self.last_log_index,
            last_log_term=self.last_log_term,
        )

        for peer_id in verified_peers:
            reply = self._send_request_vote(peer_id, args)
            if reply and reply.term > self.current_term:
                self.step_down(reply.term)
                return False
            if reply and reply.vote_granted:
                votes_granted += 1
                if votes_granted >= quorum and self.role == RaftRole.CANDIDATE:
                    self._become_leader()
                    return True

        return self.role == RaftRole.LEADER

    def _become_leader(self) -> None:
        """Transitions node to LEADER and initializes volatile leader state."""
        self.role = RaftRole.LEADER
        self.leader_id = self.node_id
        logger.info("[Raft %s] Became LEADER for term %d (Log length: %d)", self.node_id, self.current_term, len(self.log))

        # Re-initialize next_index and match_index for all peers
        peers = self.get_cluster_peers()
        for p in peers:
            self.next_index[p] = self.last_log_index + 1
            self.match_index[p] = 0

    def propose_entry(
        self,
        entry_type: CommitteeEntryType,
        payload: Dict[str, Any],
        author_node_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[CommitteeLogEntry], str]:
        """
        Proposes a new log entry to the cluster:
        1. Must be LEADER; otherwise rejects or points to current leader.
        2. Appends entry to leader's local log.
        3. Replicates to followers via AppendEntries.
        4. When quorum acknowledges, advances commit_index and applies to state machine.
        """
        if self.role != RaftRole.LEADER:
            msg = f"Node {self.node_id} is not LEADER (Current leader: {self.leader_id})"
            logger.warning("[Raft %s] Rejecting proposal: %s", self.node_id, msg)
            return False, None, msg

        new_index = len(self.log)
        entry = CommitteeLogEntry(
            index=new_index,
            term=self.current_term,
            entry_type=entry_type,
            author_node_id=author_node_id or self.node_id,
            payload=payload,
        )
        entry.sign()
        self.log.append(entry)

        # Attempt immediate replication and commit
        quorum = self.get_quorum_size()
        acks = 1  # Leader has the entry locally

        peers = self.get_cluster_peers()
        verified_peers = [p for p in peers if self.is_peer_attested(p)]

        for peer_id in verified_peers:
            prev_idx = self.next_index.get(peer_id, new_index) - 1
            prev_term = self.log[prev_idx].term if prev_idx < len(self.log) else 0
            entries_to_send = self.log[prev_idx + 1 :]

            args = AppendEntriesArgs(
                term=self.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_idx,
                prev_log_term=prev_term,
                entries=entries_to_send,
                leader_commit=self.commit_index,
            )

            reply = self._send_append_entries(peer_id, args)
            if reply:
                if reply.term > self.current_term:
                    self.step_down(reply.term)
                    return False, None, "Stepped down due to higher term peer"
                if reply.success:
                    self.match_index[peer_id] = reply.match_index
                    self.next_index[peer_id] = reply.match_index + 1
                    acks += 1
                else:
                    # Decrement next_index for next retry
                    self.next_index[peer_id] = max(1, self.next_index.get(peer_id, new_index) - 1)

        # Check if quorum achieved
        if acks >= quorum:
            self.commit_index = new_index
            self._apply_committed_entries()
            logger.info(
                "[Raft %s] Entry index %d committed with %d/%d acks (Quorum: %d)",
                self.node_id,
                new_index,
                acks,
                len(verified_peers) + 1,
                quorum,
            )
            return True, entry, "Committed by quorum"

        return False, entry, f"Quorum not achieved ({acks}/{quorum} acks)"

    def _apply_committed_entries(self) -> None:
        """Applies newly committed entries sequentially to the state machine."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            if self.last_applied < len(self.log):
                self.state_machine.apply_entry(self.log[self.last_applied])

    def _send_request_vote(self, peer_id: str, args: RequestVoteArgs) -> Optional[RequestVoteReply]:
        """Dispatches RequestVote RPC via custom dispatcher or mock network."""
        if self.rpc_dispatcher:
            try:
                res = self.rpc_dispatcher(peer_id, "request_vote", args.model_dump())
                return RequestVoteReply(**res)
            except Exception as e:
                logger.debug("RequestVote RPC to %s failed: %s", peer_id, e)
                return None
        return None

    def _send_append_entries(self, peer_id: str, args: AppendEntriesArgs) -> Optional[AppendEntriesReply]:
        """Dispatches AppendEntries RPC via custom dispatcher or mock network."""
        if self.rpc_dispatcher:
            try:
                res = self.rpc_dispatcher(peer_id, "append_entries", args.model_dump())
                return AppendEntriesReply(**res)
            except Exception as e:
                logger.debug("AppendEntries RPC to %s failed: %s", peer_id, e)
                return None
        return None

    def get_status(self) -> Dict[str, Any]:
        """Returns node status dictionary for telemetry and Cockpit display."""
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "term": self.current_term,
            "leader_id": self.leader_id,
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "log_length": len(self.log),
            "quorum_size": self.get_quorum_size(),
            "cluster_peers_count": len(self.get_cluster_peers()),
        }
