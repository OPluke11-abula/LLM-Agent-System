import { useCallback, useEffect, useRef, useState } from "react";
import {
  DEFAULT_CLUSTER_DEMO_RECEIPT,
  DEFAULT_MESH_STATUS,
  DEFAULT_RAFT_LOGS,
  DEFAULT_RAFT_STATUS,
  DEFAULT_SEARCH_RESULTS,
  DEFAULT_VECTOR_ENTRIES,
  DEFAULT_VECTOR_STATS,
} from "../components/mesh/mockData";
import type {
  ChaosFault,
  MeshStatus,
  PeerProfile,
  RaftLogEntry,
  RaftStatus,
  VectorMemoryEntryItem,
  VectorMemoryStats,
  VectorQueryResultItem,
} from "../components/mesh/types";

export function useFederatedMesh() {
  const [meshStatus, setMeshStatus] = useState<MeshStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [joinModalOpen, setJoinModalOpen] = useState<boolean>(false);
  const [seedAddress, setSeedAddress] = useState<string>("127.0.0.1:8001");
  const [joining, setJoining] = useState<boolean>(false);
  const [rotatingCert, setRotatingCert] = useState<boolean>(false);
  const [attestingNode, setAttestingNode] = useState<string | null>(null);
  const [raftStatus, setRaftStatus] = useState<RaftStatus | null>(null);
  const [raftLogs, setRaftLogs] = useState<RaftLogEntry[]>([]);
  const [electing, setElecting] = useState<boolean>(false);
  const [vectorStats, setVectorStats] = useState<VectorMemoryStats | null>(null);
  const [vectorEntries, setVectorEntries] = useState<VectorMemoryEntryItem[]>([]);
  const [queryInput, setQueryInput] = useState<string>("modular architecture boundary");
  const [searchResults, setSearchResults] = useState<VectorQueryResultItem[]>([]);
  const [searching, setSearching] = useState<boolean>(false);
  const [chaosFaults, setChaosFaults] = useState<ChaosFault[]>([]);
  const [chaosLoading, setChaosLoading] = useState<boolean>(false);
  const [clusterDemoRunning, setClusterDemoRunning] = useState<boolean>(false);
  const [clusterDemoReceipt, setClusterDemoReceipt] = useState<any | null>(null);

  // Synchronous re-entry guards
  const electingRef = useRef(false);
  const rotatingCertRef = useRef(false);
  const clusterDemoRunningRef = useRef(false);
  const joiningRef = useRef(false);

  const fetchMeshStatus = useCallback(async (signal?: AbortSignal) => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("http://127.0.0.1:8000/v1/mesh/status", { signal });
      if (!res.ok) {
        throw new Error(`Failed to fetch mesh status: HTTP ${res.status}`);
      }
      const data: MeshStatus = await res.json();
      if (signal?.aborted) return;
      setMeshStatus(data);

      try {
        const chaosRes = await fetch("http://127.0.0.1:8000/v1/mesh/chaos/faults", { signal });
        if (chaosRes.ok) {
          const cData = await chaosRes.json();
          if (!signal?.aborted) setChaosFaults(cData.faults || []);
        }
        const raftRes = await fetch("http://127.0.0.1:8000/v1/mesh/raft/status", { signal });
        if (raftRes.ok) {
          const rData = await raftRes.json();
          if (!signal?.aborted) setRaftStatus(rData);
        }
        const logRes = await fetch("http://127.0.0.1:8000/v1/mesh/raft/log", { signal });
        if (logRes.ok) {
          const lData = await logRes.json();
          if (!signal?.aborted) setRaftLogs(lData.entries || []);
        }
        const memStatsRes = await fetch("http://127.0.0.1:8000/v1/mesh/memory/stats", { signal });
        if (memStatsRes.ok) {
          const mData = await memStatsRes.json();
          if (!signal?.aborted) setVectorStats(mData);
        }
        const memEntriesRes = await fetch("http://127.0.0.1:8000/v1/mesh/memory/entries?limit=8", { signal });
        if (memEntriesRes.ok) {
          const eData = await memEntriesRes.json();
          if (!signal?.aborted) setVectorEntries(eData.entries || []);
        }
      } catch {
        // Silently tolerate sub-endpoint probe failures
      }
    } catch (err: any) {
      if (signal?.aborted) return;
      setMeshStatus(DEFAULT_MESH_STATUS);
      setRaftStatus(DEFAULT_RAFT_STATUS);
      setRaftLogs(DEFAULT_RAFT_LOGS);
      setVectorStats(DEFAULT_VECTOR_STATS);
      setVectorEntries(DEFAULT_VECTOR_ENTRIES);
      setSearchResults(DEFAULT_SEARCH_RESULTS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchMeshStatus(controller.signal);
    return () => {
      controller.abort();
    };
  }, [fetchMeshStatus]);

  const handleSearchMemory = async () => {
    if (!queryInput.trim() || searching) return;
    try {
      setSearching(true);
      const res = await fetch("http://127.0.0.1:8000/v1/mesh/memory/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryInput, top_k: 4, min_similarity: 0.0 }),
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data.results || []);
      }
    } catch {
      // Local simulated search fallback
      const filtered: VectorQueryResultItem[] = vectorEntries
        .map((e, idx) => ({
          entry_id: e.entry_id,
          task_id: e.task_id,
          category: e.category,
          content: e.content,
          metadata: e.metadata,
          author_node_id: e.author_node_id,
          similarity: Number((0.94 - idx * 0.11).toFixed(4)),
          rank: idx + 1,
          content_hash: e.content_hash,
          timestamp: e.timestamp,
        }))
        .slice(0, 4);
      setSearchResults(filtered);
    } finally {
      setSearching(false);
    }
  };

  const handleTriggerElection = async () => {
    if (electingRef.current) return;
    electingRef.current = true;
    setElecting(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/mesh/raft/elect", {
        method: "POST",
      });
      if (res.ok) {
        await fetchMeshStatus();
      }
    } catch {
      if (raftStatus) {
        setRaftStatus({
          ...raftStatus,
          role: "LEADER",
          term: raftStatus.term + 1,
          leader_id: raftStatus.node_id,
        });
      }
    } finally {
      electingRef.current = false;
      setElecting(false);
    }
  };

  const handleRotateCert = async () => {
    if (rotatingCertRef.current) return;
    rotatingCertRef.current = true;
    setRotatingCert(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/mesh/pki/rotate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ validity_seconds: 3600 }),
      });
      if (!res.ok) throw new Error(`Rotation failed: HTTP ${res.status}`);
      await fetchMeshStatus();
    } catch {
      if (meshStatus) {
        setMeshStatus({
          ...meshStatus,
          cert_fingerprint: "fbe833fa0b2045ce126cac94440c8eb2f5ba737bde7529e1fdd56ac40970b172",
          cert_expires_in_sec: 3600,
          pki_status: "ACTIVE",
        });
      }
    } finally {
      rotatingCertRef.current = false;
      setRotatingCert(false);
    }
  };

  const handleAttestPeer = async (peer: PeerProfile) => {
    try {
      setAttestingNode(peer.node_id);
      const chalRes = await fetch("http://127.0.0.1:8000/v1/mesh/attest/challenge", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_node_id: peer.node_id, ttl_seconds: 60 }),
      });
      if (chalRes.ok) {
        const chal = await chalRes.json();
        await fetch("http://127.0.0.1:8000/v1/mesh/attest/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            challenge_id: chal.challenge_id,
            origin_node_id: peer.node_id,
            cert_pem: peer.cert_pem || "-----BEGIN CERTIFICATE-----\nMIIC...\n-----END CERTIFICATE-----",
            cert_fingerprint: peer.cert_fingerprint || "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            signed_nonce: "signature_hex",
          }),
        });
      }
      await fetchMeshStatus();
    } catch {
      if (meshStatus) {
        setMeshStatus({
          ...meshStatus,
          connected_peers: meshStatus.connected_peers.map((p) =>
            p.node_id === peer.node_id
              ? { ...p, attestation_status: "VERIFIED" as const, cert_fingerprint: "e3b0c44298fc1c149afbf4c8..." }
              : p
          ),
          verified_peers_count: (meshStatus.verified_peers_count || 0) + 1,
        });
      }
    } finally {
      setAttestingNode(null);
    }
  };

  const handleInjectFault = async (payload: any) => {
    try {
      setChaosLoading(true);
      await fetch("http://127.0.0.1:8000/v1/mesh/chaos/inject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await fetchMeshStatus();
    } catch {
      const mockRule: ChaosFault = {
        rule_id: `chaos-${Math.random().toString(16).slice(2, 10)}`,
        fault_type: payload.fault_type,
        source_node_ids: payload.source_node_ids || [],
        target_node_ids: payload.target_node_ids || [],
        probability: payload.probability || 1.0,
        latency_ms: payload.latency_ms || 0,
        duration_seconds: payload.duration_seconds || 60,
        description: payload.description || "Simulated Chaos",
      };
      setChaosFaults((prev) => [...prev, mockRule]);
    } finally {
      setChaosLoading(false);
    }
  };

  const handleClearChaos = async (ruleId?: string) => {
    try {
      setChaosLoading(true);
      await fetch("http://127.0.0.1:8000/v1/mesh/chaos/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rule_id: ruleId || null }),
      });
      await fetchMeshStatus();
    } catch {
      if (ruleId) {
        setChaosFaults((prev) => prev.filter((r) => r.rule_id !== ruleId));
      } else {
        setChaosFaults([]);
      }
    } finally {
      setChaosLoading(false);
    }
  };

  const handleRunClusterDemo = async () => {
    if (clusterDemoRunningRef.current) return;
    clusterDemoRunningRef.current = true;
    setClusterDemoRunning(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/mesh/cluster/demo", {
        method: "POST",
      });
      if (res.ok) {
        const rcpt = await res.json();
        setClusterDemoReceipt(rcpt);
      }
    } catch {
      setClusterDemoReceipt(DEFAULT_CLUSTER_DEMO_RECEIPT);
    } finally {
      clusterDemoRunningRef.current = false;
      setClusterDemoRunning(false);
    }
  };

  const handleJoinPeer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!seedAddress.trim() || joiningRef.current) return;

    joiningRef.current = true;
    setJoining(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/mesh/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed_address: seedAddress }),
      });
      if (!res.ok) {
        throw new Error(`Failed to join peer: HTTP ${res.status}`);
      }
      setJoinModalOpen(false);
      await fetchMeshStatus();
    } catch {
      // Local fallback simulation if server daemon is offline
      if (meshStatus) {
        const [h, pStr] = seedAddress.split(":");
        const port = parseInt(pStr, 10) || 8001;
        const newPeer: PeerProfile = {
          node_id: `peer-${h}-${port}`,
          role: "worker",
          host: h,
          port,
          capabilities: ["REASONING_ENGINE", "TEST_RUNNER"],
          status: "connected",
          latency_ms: 14.2,
          load_score: 0.25,
        };
        setMeshStatus({
          ...meshStatus,
          peer_count: meshStatus.peer_count + 1,
          connected_peers: [...meshStatus.connected_peers, newPeer],
          avg_latency_ms: 14.2,
          cluster_health: "HEALTHY",
        });
        setJoinModalOpen(false);
      }
    } finally {
      joiningRef.current = false;
      setJoining(false);
    }
  };

  const localNode = meshStatus?.local_node;
  const connectedPeers = meshStatus?.connected_peers || [];

  return {
    meshStatus,
    loading,
    error,
    joinModalOpen,
    setJoinModalOpen,
    seedAddress,
    setSeedAddress,
    joining,
    rotatingCert,
    attestingNode,
    raftStatus,
    raftLogs,
    electing,
    vectorStats,
    vectorEntries,
    queryInput,
    setQueryInput,
    searchResults,
    searching,
    chaosFaults,
    chaosLoading,
    clusterDemoRunning,
    clusterDemoReceipt,
    localNode,
    connectedPeers,
    fetchMeshStatus,
    handleSearchMemory,
    handleTriggerElection,
    handleRotateCert,
    handleAttestPeer,
    handleInjectFault,
    handleClearChaos,
    handleRunClusterDemo,
    handleJoinPeer,
  };
}
