export interface ChaosFault {
  rule_id: string;
  fault_type: string;
  source_node_ids: string[];
  target_node_ids: string[];
  probability: number;
  latency_ms: number;
  duration_seconds?: number;
  description?: string;
  created_at?: number;
  expires_at?: number;
}

export interface PeerProfile {
  node_id: string;
  role: string;
  host: string;
  port: number;
  capabilities: string[];
  status: string;
  latency_ms: number;
  load_score: number;
  public_key_pem?: string;
  last_heartbeat?: number;
  cert_pem?: string;
  cert_fingerprint?: string;
  cert_expires_at?: string;
  attestation_status?: "PENDING" | "VERIFIED" | "REJECTED" | "EXPIRED";
  attestation_timestamp?: number;
}

export interface RaftStatus {
  node_id: string;
  role: "LEADER" | "FOLLOWER" | "CANDIDATE";
  term: number;
  leader_id: string | null;
  commit_index: number;
  last_applied: number;
  log_length: number;
  quorum_size: number;
  cluster_peers_count: number;
}

export interface RaftLogEntry {
  index: number;
  term: number;
  entry_type: string;
  author_node_id: string;
  payload: Record<string, any>;
  signature: string;
  timestamp: number;
}

export interface VectorMemoryStats {
  node_id: string;
  total_entries: number;
  merkle_root: string;
  embedding_dimension: number;
  category_breakdown: Record<string, number>;
}

export interface VectorMemoryEntryItem {
  entry_id: string;
  task_id: string;
  category: string;
  content: string;
  metadata: Record<string, any>;
  content_hash: string;
  author_node_id: string;
  timestamp: number;
}

export interface VectorQueryResultItem {
  entry_id: string;
  task_id: string;
  category: string;
  content: string;
  metadata: Record<string, any>;
  author_node_id: string;
  similarity: number;
  rank: number;
  content_hash: string;
  timestamp: number;
}

export interface MeshStatus {
  local_node: PeerProfile;
  peer_count: number;
  connected_peers: PeerProfile[];
  avg_latency_ms: number;
  cluster_health: string;
  pki_status?: string;
  cert_fingerprint?: string;
  cert_expires_in_sec?: number;
  verified_peers_count?: number;
  chaos_status?: string;
  active_chaos_faults_count?: number;
  active_chaos_faults?: ChaosFault[];
}
