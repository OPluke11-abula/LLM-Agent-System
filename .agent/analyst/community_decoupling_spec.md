# LLM-Agent-System-DEMO Decoupling Specification

This document defines the partitioning boundary between the private B2B SaaS repository (**LLM-Agent-System**) and the open-core showcase repository (**LLM-Agent-System-DEMO**).

---

## 🗺️ Decoupling Partition Matrix

| Component / File Path | Status in DEMO | Decoupling / Substitution Strategy |
| :--- | :--- | :--- |
| **`agent_workspace/core/engine.py`** | **KEEP** | Core cognitive execution loop. No changes needed. |
| **`agent_workspace/core/router.py`** | **KEEP** | Cognitive routing. Keep standard routing, remove premium tiers logic. |
| **`agent_workspace/core/billing.py`** | **DELETE** | Stripe metered billing. Remove file completely. |
| **`agent_workspace/core/sandbox.py`** | **REPLACE** | Zero-trust Docker sandbox. Replace with standard local python subprocess runner. |
| **`agent_workspace/core/merkle.py`** | **DELETE** | Deterministic binary Merkle Tree logging. Remove file completely. |
| **`agent_workspace/core/p2p_storage.py`** | **DELETE** | Peer-to-peer storage sync. Remove file completely. |
| **`agent_workspace/core/federated_sync.py`** | **DELETE** | Peer-to-peer federated sync. Remove file completely. |
| **`agent_workspace/core/cross_cloud_gateway.py`** | **DELETE** | Cross-cloud mTLS WebSocket tunneling. Remove file completely. |
| **`agent_workspace/core/audit_ledger.py`** | **REPLACE** | Immutable ledger. Replace with simple local SQLite event logger without SHA256 chaining. |
| **`agent_workspace/core/account_manager.py`** | **REPLACE** | Tenant accounts manager. Simplify to single-tenant local configs. |
| **`agent_workspace/api.py`** | **REPLACE** | REST & WebSocket API. Strip Stripe webhooks, tenant locks, rate-limiting, and P2P ECDH handshakes. Keep basic CRUD for swarms and live log streams. |
| **`agent_workspace/cli.py`** | **KEEP** | Standard developer CLI. |
| **`agent_workspace/long_term_memory.py`** | **KEEP** | Long-term memory. Keep SQLite backend; keep ChromaDB/pgvector memory backend if configured, but default to simple local SQLite memory. |
| **`agent_workspace/topology_bridge.py`** | **KEEP** | UI flow topology builder. |
| **`viewer/`** | **REPLACE** | Tauri / React UI console. Strip premium dashboard, subscription-frozen pages, and usage billing pages. Keep basic React Flow DAG view. |

---

## 🛠️ Step-by-Step Decoupling & Stubbing Plan

### 1. Stripping `billing.py` and stripe dependencies
- All Stripe API keys and metered billing database schemas are removed.
- `api.py` imports of `billing.py` are stripped.
- Subscription webhook routes (`POST /v1/stripe/webhook`) are deleted.

### 2. Stubbing `sandbox.py` (Local Execution)
- In the enterprise system, `DockerSandbox` spawns sandboxed execution inside strict Docker containers.
- In the community DEMO, replace with `LocalProcessSandbox` which runs python code locally via python's `subprocess.run` / `exec()`.

### 3. Cleaning `api.py` and Security Controls
- Remove the token rate-limiting (sliding window of 5k TPM) or make it a simple local counter.
- Remove JWT token validation for multiple tenants. Replace with a single-user auth token or no auth (open localhost dashboard).
- Remove ECDH dynamic connection guard validation on WebSockets.

### 4. Updating `README.md`
- Provide a clean, developer-focused README for `LLM-Agent-System-DEMO` outlining how to run it locally without Docker or Stripe.
