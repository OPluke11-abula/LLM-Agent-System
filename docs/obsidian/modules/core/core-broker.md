---
tags:
  - architecture/leaf
  - runtime/pubsub
  - broker/distributed
  - layer/l7
type: module_leaf
layer: L7-Distributed-Mesh-and-P2P
module: agent_workspace.core.broker
file_path: agent_workspace/core/broker.py
sync_status: verified
---

# Module: SwarmBroker (In-Memory & Redis Pub/Sub Event Mesh)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Provides decoupled, asynchronous publish/subscribe messaging infrastructure connecting swarm agent nodes, telemetry collectors, and websocket relays.
- **Invariant**: Subscribers receive ordered messages per channel; broker shutdown cleanly drains and unsubscribes all active listener queues without memory leaks.
- **Data Flow**: Buffers events from [[core-discussion-room]], [[core-router]], and [[core-ws-manager]], dispatching to local asyncio queues or remote Redis pub/sub channels.

---

## 2. Source Code & Symbol Mapping

**Source Location**: [broker.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/core/broker.py) (206 lines)

### Symbol Table

| Symbol | Kind | Line Range | Description |
| :--- | :--- | :--- | :--- |
| BaseSwarmBroker | class | L14-L28 | Abstract base class specifying the pub/sub contract (publish, subscribe, unsubscribe). |
| InMemorySwarmBroker | class | L31-L83 | High-performance in-process event broker utilizing asyncio.Queue for local topologies. |
| publish | def | L38-L42 | Distributes messages to all registered channel queues with monotonic order. |
| subscribe | def | L44-L67 | Registers an async callback listener to a specific topic channel. |
| unsubscribe | def | L69-L74 | Removes a listener callback from a topic channel. |
| stop | def | L76-L83 | Cancels all active background queue consumer tasks. |
| RedisSwarmBroker | class | L105-L187 | Distributed broker implementation using Redis Pub/Sub channels for multi-host swarms. |
| start / stop | def | L115-L138 | Manages Redis connection lifecycle and consumer threads. |
| _listen_loop | def | L161-L187 | Asynchronous worker loop deserializing Redis messages and dispatching to callbacks. |
| get_broker | def | L206-L225 | Factory method returning configured broker instance (Redis if configured, falling back to InMemory). |

---

## 3. Pub/Sub Broker Topology

`mermaid
graph LR
    subgraph Producers[Publishers]
        R[AgentRouter]
        D[DiscussionRoom]
        W[WorkflowEngine]
    end

    subgraph BrokerMesh[SwarmBroker Core]
        B[(InMemory / Redis Broker)]
    end

    subgraph Consumers[Subscribers]
        WS[CrewSyncManager / WebSockets]
        UI[Viewer Frontend Cockpit]
        A[AuditConsensusDaemon]
    end

    R -->|publish(event)| B
    D -->|publish(consensus)| B
    W -->|publish(step_status)| B
    B -->|deliver| WS
    B -->|deliver| UI
    B -->|deliver| A
`

---

## 4. Operational Invariants & Anti-Corruption Guardrails
1. **Graceful Fallback**: If Redis connectivity fails on initialization, the system gracefully falls back to InMemorySwarmBroker with a warning log.
2. **Channel Isolation**: Topic channels (	elemetry, logs, governance, ledger) are isolated; errors in one handler never terminate the distribution loop for other channels.

---

## 5. Verification & Test Evidence
- **Test Suites**:
  - [	est_distributed_broker.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_distributed_broker.py)
  - [	est_tenant_channels.py](file:///d:/GitHub/LLM-Agent-System/agent_workspace/tests/test_tenant_channels.py)
- **Execution Receipt**: Bytecode validated via compileall exit code 0.

---

## 6. Topological Linkage
- **Upstream Layer**: [[L7-Distributed-Mesh-and-P2P]]
- **Control Plane**: [[10 7-Layer System Architecture & Control Plane Topology]]
- **Collaborating Modules**:
  - [[core-ws-manager]]
  - [[core-discussion-room]]
  - [[core-p2p-router]]
