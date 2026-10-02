import React from "react";
import type { Lang } from "../types";
import { useFederatedMesh } from "../hooks/useFederatedMesh";
import { ChaosConsoleCard } from "./mesh/ChaosConsoleCard";
import { ClusterDemoCard } from "./mesh/ClusterDemoCard";
import { ConnectedPeersSection } from "./mesh/ConnectedPeersSection";
import { JoinPeerModal } from "./mesh/JoinPeerModal";
import { LocalCapabilitiesBanner } from "./mesh/LocalCapabilitiesBanner";
import { MeshHeader } from "./mesh/MeshHeader";
import { MeshKpiGrid } from "./mesh/MeshKpiGrid";
import { PkiAttestationCard } from "./mesh/PkiAttestationCard";
import { RaftConsensusCard } from "./mesh/RaftConsensusCard";
import { VectorMemoryCard } from "./mesh/VectorMemoryCard";
import type {
  ChaosFault,
  MeshStatus,
  PeerProfile,
  RaftLogEntry,
  RaftStatus,
  VectorMemoryEntryItem,
  VectorMemoryStats,
  VectorQueryResultItem,
} from "./mesh/types";

export type {
  ChaosFault,
  MeshStatus,
  PeerProfile,
  RaftLogEntry,
  RaftStatus,
  VectorMemoryEntryItem,
  VectorMemoryStats,
  VectorQueryResultItem,
};

interface FederatedMeshViewProps {
  lang?: Lang;
}

export const FederatedMeshView: React.FC<FederatedMeshViewProps> = ({ lang: _lang = "en" }) => {
  const {
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
  } = useFederatedMesh();

  return (
    <div className="flex h-full flex-col overflow-y-auto bg-[var(--bg)] p-6 text-[var(--t1)]">
      <MeshHeader
        loading={loading}
        onRefresh={() => fetchMeshStatus()}
        onOpenJoinModal={() => setJoinModalOpen(true)}
      />

      {error && (
        <div className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-400">
          {error}
        </div>
      )}

      <MeshKpiGrid
        localNode={localNode}
        meshStatus={meshStatus}
        connectedPeers={connectedPeers}
        raftStatus={raftStatus}
      />


      {/* Zero-Trust mTLS PKI Identity & Attestation Bar */}
      <PkiAttestationCard
        meshStatus={meshStatus}
        localNode={localNode}
        rotatingCert={rotatingCert}
        onRotateCert={handleRotateCert}
      />

      {/* Raft Committee Consensus & Replicated Ledger Panel */}
      <RaftConsensusCard
        raftStatus={raftStatus}
        raftLogs={raftLogs}
        electing={electing}
        onTriggerElection={handleTriggerElection}
      />

      {/* Federated Vector Memory & RAG Knowledge Topology Panel */}
      <VectorMemoryCard
        vectorStats={vectorStats}
        vectorEntries={vectorEntries}
        queryInput={queryInput}
        setQueryInput={setQueryInput}
        searching={searching}
        searchResults={searchResults}
        onSearch={handleSearchMemory}
      />

      {/* Local Capabilities Banner */}
      <LocalCapabilitiesBanner localNode={localNode} />

      {/* Chaos Fault Injection & Multi-Worker Cluster Demo */}
      <div className="mb-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChaosConsoleCard
          chaosFaults={chaosFaults}
          chaosLoading={chaosLoading}
          localNode={localNode}
          onInjectFault={handleInjectFault}
          onClearChaos={handleClearChaos}
        />

        <ClusterDemoCard
          clusterDemoRunning={clusterDemoRunning}
          clusterDemoReceipt={clusterDemoReceipt}
          onRunClusterDemo={handleRunClusterDemo}
        />
      </div>

      {/* Connected Peers Section */}
      <ConnectedPeersSection
        connectedPeers={connectedPeers}
        attestingNode={attestingNode}
        onAttestPeer={handleAttestPeer}
        onOpenJoinModal={() => setJoinModalOpen(true)}
      />

      {/* Join Seed Peer Modal */}
      <JoinPeerModal
        isOpen={joinModalOpen}
        onClose={() => setJoinModalOpen(false)}
        seedAddress={seedAddress}
        setSeedAddress={setSeedAddress}
        joining={joining}
        onSubmit={handleJoinPeer}
      />
    </div>
  );
};
