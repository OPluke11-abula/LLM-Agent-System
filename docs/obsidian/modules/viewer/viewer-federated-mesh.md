---
tags:
  - architecture/leaf
  - frontend/mesh
  - p2p/cluster
  - layer/l1
  - protocol/v3-8-0
type: module_leaf
layer: L1-Ingress-and-Cockpit-Surface
module: viewer.components.FederatedMeshView
file_path: viewer/src/components/FederatedMeshView.tsx
sync_status: verified
---

# Module: FederatedMeshView (Federated P2P Mesh & Cluster Control Plane)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Production-grade developer control plane for distributed P2P swarm mesh, zero-trust dynamic PKI attestation, Raft consensus state machine, federated vector memory, chaos fault injection, and multi-worker cluster demonstration.
- **Invariant**: Every mutating action is guarded by synchronous `useRef` locks (`electingRef`, `rotatingCertRef`, `clusterDemoRunningRef`, `joiningRef`) preventing race conditions, and all asynchronous fetch subscriptions use `AbortController` to guarantee clean unmounting.
- **Data Flow**: Consumes REST endpoints (`/v1/mesh/*`) and WebSocket streams from `agent_workspace/routes/mesh.py`, coordinating modular subcomponents in `viewer/src/components/mesh/`.

---

## 2. Source Code & Modular Decomposition

**Source Location**: [`FederatedMeshView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/FederatedMeshView.tsx) (596 lines)
**Modular Package**: `viewer/src/components/mesh/` (Phase 97 extraction)

### Subcomponent & Symbol Mapping

| Symbol / Component | File Location | Line Count | Description |
| :--- | :--- | :--- | :--- |
| `FederatedMeshView` | [`FederatedMeshView.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/FederatedMeshView.tsx) | 596 lines | Root mesh control plane coordinating node status, live tabs, async mutations, and error states. |
| `LocalCapabilitiesBanner` | [`mesh/LocalCapabilitiesBanner.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/LocalCapabilitiesBanner.tsx) | 48 lines | Banner displaying local node ID, endpoint, operational capabilities, and status badges. |
| `ConnectedPeersSection` | [`mesh/ConnectedPeersSection.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/ConnectedPeersSection.tsx) | 92 lines | Mesh topology ledger showing peer connection status, latency, roles, and attestation level. |
| `PkiAttestationCard` | [`mesh/PkiAttestationCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/PkiAttestationCard.tsx) | 128 lines | Zero-Trust dynamic node attestation, certificate fingerprint, expiration countdown, and rotation trigger. |
| `RaftConsensusCard` | [`mesh/RaftConsensusCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/RaftConsensusCard.tsx) | 142 lines | Distributed Raft consensus status, active term, leader node, election trigger, and replicated log ledger. |
| `VectorMemoryCard` | [`mesh/VectorMemoryCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/VectorMemoryCard.tsx) | 165 lines | Federated vector memory dashboard with cosine similarity search bar, Merkle root, and synced entry count. |
| `ChaosConsoleCard` | [`mesh/ChaosConsoleCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/ChaosConsoleCard.tsx) | 134 lines | Chaos fault injection console for network partition, latency spikes, packet drops, and active fault rules. |
| `ClusterDemoCard` | [`mesh/ClusterDemoCard.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/ClusterDemoCard.tsx) | 158 lines | 7-stage multi-worker cluster demonstration runner, scorecards, and verifiable execution receipts. |
| `JoinPeerModal` | [`mesh/JoinPeerModal.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/JoinPeerModal.tsx) | 98 lines | Modal dialog for connecting to remote mesh peers via endpoint URL and credentials. |
| `mockData.ts` | [`mesh/mockData.ts`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/mockData.ts) | 115 lines | Offline/fallback mock data for cluster demo receipts, raft logs, vector entries, and peer profiles. |
| `types.ts` | [`mesh/types.ts`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/mesh/types.ts) | 52 lines | TypeScript definitions for mesh status, Raft state, vector entries, and chaos fault rules. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Synchronous Mutation Locks**: Guarded by `useRef` locks to guarantee that multiple clicks on `Trigger Raft Election`, `Rotate Certificate`, or `Run Cluster Demo` cannot trigger concurrent requests.
2. **Lifecycle Unmount Guarding**: Asynchronous data loading uses `AbortController` and `isSubscribed` flag to cleanly abort in-flight fetch requests when the view unmounts.
3. **Zero-Trust Attestation Display**: Clear visual cues distinguish between `VERIFIED`, `QUARANTINED`, and `UNVERIFIED` nodes.
4. **HMR Fast Refresh Compliance**: Utility functions are decoupled to `viewer/src/components/ui/utils.ts`.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Rolldown/Vite production build succeeded in 785ms with 0 errors (`npm run build` in `viewer/`).
- **React Doctor Scorecard**: 0 Bugs, 0 Performance regressions, 0 Accessibility violations.
- **UI Smoke & Swarm Verification**: `npm run verify:ui` and `npm run test:swarm-ui` PASS.
- **Backend API Parity**: Verified with FastAPI backend router `agent_workspace/routes/mesh.py`.

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Distributed Layer**: [[L7-Distributed-Mesh-and-P2P]]
- **Backend Coordinator**: [[core-federated-mesh]]
- **Security PKI**: [[core-mesh-pki]]
- **Consensus Engine**: [[core-raft-consensus]]
- **Memory Engine**: [[core-vector-memory]]
- **Chaos Engine**: [[core-chaos-and-self-healing]]
- **Parent Shell**: [[viewer-app]]
