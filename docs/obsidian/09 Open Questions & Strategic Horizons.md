---
tags:
  - strategy/roadmap
  - open-questions
  - architecture/horizon
type: strategic_questions
layer: L2-Protocol-and-Contract-Gateways
sync_status: verified
---

# Open Questions & Strategic Horizons (09)

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **Related Notes**: [[05 Task Status & Multi-Agent Execution DAG]], [[60 Architectural Decision Records (ADR) Graph]]
> **Protocol Version**: `3.8.0`

---

## 1. Active Strategic Questions & Implementation Resolutions

### Q-001: Multi-Agent Model Selection & Cost Balancing
- **Question**: When dispatching across the 10 Grounded Roles, how should model families be dynamically selected to optimize latency versus reasoning depth without blowing the token budget?
- **Status**: **`RESOLVED & CERTIFIED`**
- **Concrete Implementation**:
  - `ARCHITECT_PLANNER_AGENT`, `DOMAIN_LOGIC_AGENT`, `SECURITY_AUDIT_AGENT` default to reasoning models (`pro` / Claude 3.7 Sonnet).
  - `APPLICATION_FLOW_AGENT`, `QA_TEST_AGENT`, `KNOWLEDGE_TOPOLOGY_AGENT` utilize high-throughput models (`flash` / Claude 3.5 Haiku).
  - Downscaling policy is dynamically evaluated by `SwarmCoordinator.should_downscale_model(workspace_path, tenant_id)` in `agent_workspace/core/swarm_coordinator.py:195` (triggers when remaining credits < 20% of max budget and routing_policy == 'downscale').
  - Verified by dedicated regression suite: `agent_workspace/tests/test_swarm_adaptive_billing.py` (100% PASS).

### Q-002: Dual Knowledge Mirror Freshness vs Git Footprint
- **Question**: Should the Obsidian Vault notes live strictly inside `docs/obsidian/` in the Git repository, or maintain live real-time bidirectional syncing with the local Obsidian Vault at `C:\Users\luke2\OneDrive\文件\Obsidian Vault`?
- **Status**: **`RESOLVED & CERTIFIED (ADR-002)`**
- **Concrete Implementation**:
  - Both surfaces remain identical in topology. `docs/obsidian/` is tracked in Git as the durable repository truth.
  - The local vault is synchronized upon each verification milestone by `KNOWLEDGE_TOPOLOGY_AGENT`, ensuring local Obsidian desktop visual graph access without introducing machine-local noise into Git.
  - Linter UTF-8 encoding support in `.agent/knowledge_base/tools/lint_obsidian_vault.ps1` and `lint_knowledge_base.ps1` ensures zero mojibake across platforms.

### Q-003: Concurrency Control in Heterogeneous Environments
- **Question**: How should `latest-request-wins` be maintained across multi-node or distributed broker setups (Redis vs In-Memory)?
- **Status**: **`RESOLVED & CERTIFIED`**
- **Concrete Implementation**:
  - All asynchronous request streams carry an incremental monotonically increasing `epoch_id` and `request_id`.
  - Stale results arriving with an `epoch_id < current_epoch` are atomically discarded at the event loop boundary before updating state.
  - Multi-node state machine replication is governed by distributed Raft consensus in `agent_workspace/core/raft_consensus.py` and validated by `agent_workspace/tests/test_raft_consensus_p89.py`.
