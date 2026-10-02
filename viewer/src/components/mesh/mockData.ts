import type {
  MeshStatus,
  PeerProfile,
  RaftLogEntry,
  RaftStatus,
  VectorMemoryEntryItem,
  VectorMemoryStats,
  VectorQueryResultItem,
} from "./types";

export const DEFAULT_LOCAL_NODE: PeerProfile = {
  node_id: "node-local-lead",
  role: "architect",
  host: "127.0.0.1",
  port: 8000,
  capabilities: ["COCKPIT_LEADER", "REASONING_ENGINE"],
  status: "connected",
  latency_ms: 0.0,
  load_score: 0.15,
  cert_fingerprint: "36b033fd22c2bdbf58f0d43dbc8ef87975b67624a1d0ef73ed214eb0802b3fce",
  attestation_status: "VERIFIED",
};

export const DEFAULT_MESH_STATUS: MeshStatus = {
  local_node: DEFAULT_LOCAL_NODE,
  peer_count: 0,
  connected_peers: [],
  avg_latency_ms: 0.0,
  cluster_health: "STANDALONE",
  pki_status: "ACTIVE",
  cert_fingerprint: "36b033fd22c2bdbf58f0d43dbc8ef87975b67624a1d0ef73ed214eb0802b3fce",
  cert_expires_in_sec: 3600,
  verified_peers_count: 0,
};

export const DEFAULT_RAFT_STATUS: RaftStatus = {
  node_id: "node-local-lead",
  role: "LEADER",
  term: 1,
  leader_id: "node-local-lead",
  commit_index: 2,
  last_applied: 2,
  log_length: 3,
  quorum_size: 1,
  cluster_peers_count: 0,
};

export const DEFAULT_RAFT_LOGS: RaftLogEntry[] = [
  {
    index: 0,
    term: 0,
    entry_type: "CONFIGURATION",
    author_node_id: "genesis",
    payload: { desc: "genesis_slot" },
    signature: "36b033fd22c2bdbf...",
    timestamp: Date.now() / 1000 - 300,
  },
  {
    index: 1,
    term: 1,
    entry_type: "SPEECH_TURN",
    author_node_id: "node-local-lead",
    payload: { task_id: "TASK-001", speaker: "architect", content: "Scoped boundary verified." },
    signature: "8f7e2a1b9c0d...",
    timestamp: Date.now() / 1000 - 120,
  },
  {
    index: 2,
    term: 1,
    entry_type: "CONSENSUS_VERDICT",
    author_node_id: "node-local-lead",
    payload: { task_id: "TASK-001", decision: "CONSENSUS_APPROVED", composite_score: 0.95 },
    signature: "1c2d3e4f5a6b...",
    timestamp: Date.now() / 1000 - 60,
  },
];

export const DEFAULT_VECTOR_STATS: VectorMemoryStats = {
  node_id: "node-local-lead",
  total_entries: 3,
  merkle_root: "9e4a8b2c1f0d3e5a7b9c1d3e5f7a9b1c3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a",
  embedding_dimension: 1536,
  category_breakdown: {
    DECISION: 1,
    PATTERN: 1,
    LESSON: 1,
  },
};

export const DEFAULT_VECTOR_ENTRIES: VectorMemoryEntryItem[] = [
  {
    entry_id: "vec-001",
    task_id: "TASK-089",
    category: "DECISION",
    content: "Enforce CommitteeRaftNode quorum consensus before executing production git mutations.",
    metadata: { composite_score: 0.96, decision: "CONSENSUS_APPROVED" },
    content_hash: "a1b2c3d4e5f67890abcdef1234567890",
    author_node_id: "node-local-lead",
    timestamp: Date.now() / 1000 - 180,
  },
  {
    entry_id: "vec-002",
    task_id: "TASK-088",
    category: "PATTERN",
    content: "Zero-Trust mTLS attestation challenge-response handshake gates untrusted peer participation.",
    metadata: { composite_score: 0.94, decision: "CONSENSUS_APPROVED" },
    content_hash: "b2c3d4e5f67890a1bcdef1234567890a",
    author_node_id: "node-local-lead",
    timestamp: Date.now() / 1000 - 360,
  },
  {
    entry_id: "vec-003",
    task_id: "TASK-087",
    category: "LESSON",
    content: "Multi-module task mutations without decoupled interfaces trigger Extreme Single Responsibility objections.",
    metadata: { composite_score: 0.65, decision: "REJECTED_NEEDS_REVISION" },
    content_hash: "c3d4e5f67890a1b2cdef1234567890ab",
    author_node_id: "node-local-lead",
    timestamp: Date.now() / 1000 - 720,
  },
];

export const DEFAULT_SEARCH_RESULTS: VectorQueryResultItem[] = [
  {
    entry_id: "vec-001",
    task_id: "TASK-089",
    category: "DECISION",
    content: "Enforce CommitteeRaftNode quorum consensus before executing production git mutations.",
    metadata: { composite_score: 0.96 },
    author_node_id: "node-local-lead",
    similarity: 0.9241,
    rank: 1,
    content_hash: "a1b2c3d4...",
    timestamp: Date.now() / 1000 - 180,
  },
  {
    entry_id: "vec-003",
    task_id: "TASK-087",
    category: "LESSON",
    content: "Multi-module task mutations without decoupled interfaces trigger Extreme Single Responsibility objections.",
    metadata: { composite_score: 0.65 },
    author_node_id: "node-local-lead",
    similarity: 0.8115,
    rank: 2,
    content_hash: "c3d4e5f6...",
    timestamp: Date.now() / 1000 - 720,
  },
];

export const DEFAULT_CLUSTER_DEMO_RECEIPT = {
  demo_id: "demo-static-receipt",
  nodes_participating: ["cluster-node-1", "cluster-node-2", "cluster-node-3"],
  total_steps: 7,
  passed_steps: 7,
  success: true,
  duration_total_ms: 684.5,
  step_receipts: [
    { step_name: "1. Zero-Trust mTLS Mutual Attestation", status: "PASS", duration_ms: 224.8 },
    { step_name: "2. Raft Consensus Leader Election", status: "PASS", duration_ms: 0.2 },
    { step_name: "3. Federated Vector Memory Merkle Sync", status: "PASS", duration_ms: 14.5 },
    { step_name: "4. Chaos Network Partition Isolation", status: "PASS", duration_ms: 0.3 },
    { step_name: "5. Majority Partition Raft Leader Failover", status: "PASS", duration_ms: 0.2 },
    { step_name: "6. Partition Resolution & Leader Step-Down", status: "PASS", duration_ms: 0.1 },
    { step_name: "7. Autonomous Self-Healing & Auto-Rollback Engine", status: "PASS", duration_ms: 444.4 },
  ],
};
