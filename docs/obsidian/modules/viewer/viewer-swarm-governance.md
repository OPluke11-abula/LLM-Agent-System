---
tags:
  - architecture/leaf
  - frontend/governance
  - swarm/mtls
  - layer/l1
type: module_leaf
layer: L1-Ingress-and-Cockpit-Surface
module: viewer.components.SwarmGovernanceConsole
file_path: viewer/src/components/SwarmGovernanceConsole.tsx
sync_status: verified
---

# Module: SwarmGovernanceConsole (Mesh Monitor, mTLS Status & ZK Proofs)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Governance cockpit monitoring distributed swarm health, P2P mesh peers, mutual TLS certificate rotation countdowns, cryptographic proofs, and swarm replays.
- **Invariant**: Quarantined nodes identified by `SwarmIDS` are immediately highlighted in hazard red with disabled interaction controls.
- **Data Flow**: Fetches node statuses, mTLS certificates, and Merkle inclusion proofs via REST endpoints, syncing real-time failover events over WebSockets.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [`SwarmGovernanceConsole.tsx`](file:///d:/GitHub/LLM-Agent-System/viewer/src/components/SwarmGovernanceConsole.tsx) (2050 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| `SwarmGovernanceConsole` | `function` | L1971-L1980 | Entry point rendering top-level governance overview and panel grid. |
| `useSwarmGovernanceController`| `hook` | L1564-L1965 | Controller fetching node telemetry, managing polling cycles, and handling replay state. |
| `SwarmNodeMonitor` | `component` | L945-L1010 | Node grid displaying status, active role, current memory usage, and heartbeat timer. |
| `SessionFailoverDashboard` | `component` | L1015-L1065 | Visualizes automated session migration between primary and fallback nodes. |
| `P2PMeshNetworkMap` | `component` | L1070-L1108 | Displays active P2P mesh topology, round-trip latency, and shared key status. |
| `MTLSTunnelingStatusPanel` | `component` | L1111-L1230 | Certificate health monitor showing fingerprint, SANs, and rotation countdown. |
| `BillingPolicyControls` | `component` | L1299-L1355 | Tenant budget controls, credit allocation slider, and rate-limiting toggles. |
| `CryptographicProofInspector` | `component` | L1359-L1465 | Interactive Merkle tree viewer and Zero-Knowledge proof validator widget. |
| `ReplayPlaybackWidget` | `component` | L1469-L1560 | Scrubbable timeline for replaying past swarm consensus decisions step-by-step. |

---

## 3. Operational Invariants & Anti-Corruption Guardrails
1. **Certificate Expiration Warning**: Countdown timers under 1 hour render glowing amber alerts advising manual key rotation if auto-rotation fails.
2. **Deterministic Replay**: Swarm replay widgets read directly from verified cryptographic logs without mock approximations.

---

## 4. Verification & Test Evidence
- **Build Receipt**: Vite build validated clean exit code 0.

---

## 5. Topological Linkage
- **Upstream Layer**: [[L1-Ingress-and-Cockpit-Surface]]
- **Backend Counterparts**:
  - [[core-cert-manager]]
  - [[core-audit-ledger]]
  - [[core-p2p-router]]
