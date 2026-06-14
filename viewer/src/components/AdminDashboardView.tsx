import { useCallback, useEffect, useState } from "react";
import {
  Background,
  BackgroundVariant,
  ReactFlow,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { Button, ProgressBar, StatusBadge, Surface, toneForStatus } from "./ui/primitives";
import type { TranslationMessages } from "../types";

type AdminDashboardViewProps = {
  theme: string;
  t: TranslationMessages;
};

type TenantInfo = {
  tenant_id: string;
  status: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  last_updated: string;
  api_key: string;
  total_tokens: number;
  total_cost_usd: number;
  tokens_last_minute: number;
};

type AuditBlock = {
  id: number;
  event_type: string;
  payload: string;
  previous_hash: string;
  current_hash: string;
  timestamp: string;
  tenant_id: string;
};

export function AdminDashboardView({ t }: AdminDashboardViewProps) {
  // 1. Tenants & Billing state
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [errorTenants, setErrorTenants] = useState<string | null>(null);
  const [rotatedKeyInfo, setRotatedKeyInfo] = useState<{ [tenantId: string]: string }>({});

  // 2. Swarm Interceptor State
  const [selectedSessionId] = useState("default");
  const [swarmStatus, setSwarmStatus] = useState("running");
  const [hijackText, setHijackText] = useState("");
  const [showHijackInput, setShowHijackInput] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [swarmNodes, setSwarmNodes, onSwarmNodesChange] = useNodesState([]);
  const [swarmEdges, setSwarmEdges, onSwarmEdgesChange] = useEdgesState([]);
  const [lastInteractedAgent, setLastInteractedAgent] = useState<string | null>(null);
  const [activeTelemetry, setActiveTelemetry] = useState<{
    latencyMs: number;
    billingUsd: number;
    lastMessage: string;
  }>({ latencyMs: 0, billingUsd: 0.0, lastMessage: "Swarm initialized." });

  // 3. Ledger Visualizer State
  const [auditBlocks, setAuditBlocks] = useState<AuditBlock[]>([]);
  const [auditStatus, setAuditStatus] = useState<{
    valid: boolean;
    tampered_id: number | null;
    merkle_root: string;
  }>({ valid: true, tampered_id: null, merkle_root: "" });
  const [checkingLedger, setCheckingLedger] = useState(false);
  const [ledgerNodes, setLedgerNodes, onLedgerNodesChange] = useNodesState([]);
  const [ledgerEdges, setLedgerEdges, onLedgerEdgesChange] = useEdgesState([]);

  // Fetch Tenants Data
  const fetchTenants = useCallback(async () => {
    try {
      const resp = await fetch("http://localhost:8000/v1/admin/tenants", {
        headers: { "x-api-key": "key-admin" }
      });
      if (!resp.ok) {
        throw new Error(`Failed to load tenants: ${resp.statusText}`);
      }
      const data = await resp.json();
      if (data.status === "success") {
        setTenants(data.tenants || []);
        setErrorTenants(null);
      }
    } catch (err: any) {
      setErrorTenants(err.message || "Unknown error");
    } finally {
      setLoadingTenants(false);
    }
  }, []);

  // Fetch Ledger Audit Data
  const fetchLedger = useCallback(async () => {
    setCheckingLedger(true);
    try {
      // 1. Fetch Audit Status
      const statusResp = await fetch("http://localhost:8000/v1/audit/status", {
        headers: { "x-api-key": "key-admin" }
      });
      const statusData = await statusResp.json();
      
      // 2. Fetch Audit Logs
      const logsResp = await fetch("http://localhost:8000/v1/audit/logs", {
        headers: { "x-api-key": "key-admin" }
      });
      const logsData = await logsResp.json();

      if (statusData.status === "success" && logsData.status === "success") {
        setAuditStatus({
          valid: statusData.valid,
          tampered_id: statusData.tampered_id,
          merkle_root: statusData.merkle_root
        });
        setAuditBlocks(logsData.logs || []);
      }
    } catch (err) {
      console.error("Failed to load audit ledger data:", err);
    } finally {
      setCheckingLedger(false);
    }
  }, []);

  // Key rotation handler
  const handleRotateKey = async (tenantId: string) => {
    try {
      const resp = await fetch("http://localhost:8000/v1/admin/tenants/rotate-key", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": "key-admin"
        },
        body: JSON.stringify({ tenant_id: tenantId })
      });
      const data = await resp.json();
      if (data.status === "success") {
        setRotatedKeyInfo(prev => ({ ...prev, [tenantId]: data.api_key }));
        fetchTenants();
      }
    } catch (err) {
      alert(`Key rotation failed: ${err}`);
    }
  };

  // Status simulation handler
  const handleUpdateSubscription = async (tenantId: string, status: string) => {
    try {
      const resp = await fetch("http://localhost:8000/v1/admin/tenants/update-subscription", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": "key-admin"
        },
        body: JSON.stringify({ tenant_id: tenantId, status })
      });
      const data = await resp.json();
      if (data.status === "success") {
        fetchTenants();
      }
    } catch (err) {
      alert(`Status update failed: ${err}`);
    }
  };

  // Swarm controls
  const handlePauseSwarm = async () => {
    try {
      const resp = await fetch(`http://localhost:8000/v1/sessions/${selectedSessionId}/pause`, {
        method: "POST",
        headers: { "x-api-key": "key-admin" }
      });
      const data = await resp.json();
      if (data.status === "success") {
        setSwarmStatus("paused");
      }
    } catch (err) {
      alert(`Failed to pause: ${err}`);
    }
  };

  const handleResumeSwarm = async () => {
    try {
      const resp = await fetch(`http://localhost:8000/v1/sessions/${selectedSessionId}/resume`, {
        method: "POST",
        headers: { "x-api-key": "key-admin" }
      });
      const data = await resp.json();
      if (data.status === "success") {
        setSwarmStatus("running");
      }
    } catch (err) {
      alert(`Failed to resume: ${err}`);
    }
  };

  const handleHijackInput = async () => {
    if (!hijackText.trim()) return;
    try {
      const resp = await fetch(`http://localhost:8000/v1/sessions/${selectedSessionId}/hijack`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": "key-admin"
        },
        body: JSON.stringify({ hijack_value: hijackText })
      });
      const data = await resp.json();
      if (data.status === "success") {
        alert("Hijack command dispatched successfully!");
        setHijackText("");
        setShowHijackInput(false);
      }
    } catch (err) {
      alert(`Hijack failed: ${err}`);
    }
  };

  // Initialize data on load
  useEffect(() => {
    fetchTenants();
    fetchLedger();
  }, [fetchTenants, fetchLedger]);

  // Swarm WebSockets & Mock Canvas Loop
  useEffect(() => {
    let ws: WebSocket | null = null;
    let mockInterval: any = null;
    let currentActiveIdx = 0;

    const agents = ["CEO", "Developer", "QA", "CFO"];
    const positions = [
      { x: 120, y: 60 },
      { x: 380, y: 60 },
      { x: 250, y: 220 },
      { x: 500, y: 220 }
    ];

    const initialNodes = agents.map((agent, i) => ({
      id: agent,
      data: { label: agent },
      position: positions[i],
      style: {
        background: "var(--bg-card)",
        borderColor: "var(--border-c)",
        color: "var(--t1)",
        borderRadius: "12px",
        padding: "10px 16px",
        fontSize: "13px",
        fontWeight: "bold",
        borderWidth: "1.5px"
      }
    }));

    const initialEdges = [
      { id: "ceo-dev", source: "CEO", target: "Developer", animated: false, style: { stroke: "var(--border-c)", strokeWidth: 1.5 } },
      { id: "dev-qa", source: "Developer", target: "QA", animated: false, style: { stroke: "var(--border-c)", strokeWidth: 1.5 } },
      { id: "qa-cfo", source: "QA", target: "CFO", animated: false, style: { stroke: "var(--border-c)", strokeWidth: 1.5 } },
      { id: "cfo-ceo", source: "CFO", target: "CEO", animated: false, style: { stroke: "var(--border-c)", strokeWidth: 1.5 } }
    ];

    setSwarmNodes(initialNodes);
    setSwarmEdges(initialEdges);

    // 1. Establish WebSocket Connection
    try {
      ws = new WebSocket(`ws://localhost:8000/v1/collaboration/${selectedSessionId}?api_key=key-admin`);
      
      ws.onopen = () => {
        setWsConnected(true);
        ws?.send(JSON.stringify({ handshake: "bypass" }));
        ws?.send(JSON.stringify({ action: "subscribe", channel: "logs" }));
        ws?.send(JSON.stringify({ action: "subscribe", channel: "topology" }));
      };

      ws.onmessage = (event) => {
        try {
          const rawData = JSON.parse(event.data);
          if (rawData.payload) {
            const payload = rawData.payload;
            const fromAgent = payload.agent || "CEO";
            const messageText = payload.event || "Debate Round Tick";
            const delay = rawData.duration_ms || 450;
            const tokenCost = (rawData.token_used || 180) * 0.00015;

            setLastInteractedAgent(fromAgent);
            setActiveTelemetry({
              latencyMs: delay,
              billingUsd: tokenCost,
              lastMessage: messageText
            });

            // Make the node glow dynamically
            setSwarmNodes(nodes =>
              nodes.map(node => ({
                ...node,
                style: {
                  ...node.style,
                  borderColor: node.id === fromAgent ? "var(--accent)" : "var(--border-c)",
                  boxShadow: node.id === fromAgent ? "var(--ring)" : "none"
                }
              }))
            );

            // Animate target edge
            setSwarmEdges(edges =>
              edges.map(edge => ({
                ...edge,
                animated: edge.source === fromAgent,
                style: {
                  ...edge.style,
                  stroke: edge.source === fromAgent ? "var(--accent)" : "var(--border-c)",
                  strokeWidth: edge.source === fromAgent ? 2.5 : 1.5
                }
              }))
            );
          }
        } catch (e) {
          // Silent parsing errors
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
      };
      ws.onerror = () => {
        setWsConnected(false);
      };
    } catch (err) {
      setWsConnected(false);
    }

    // 2. Offline Mock Simulation (Activates when WebSocket is down or inactive)
    if (!wsConnected) {
      mockInterval = setInterval(() => {
        if (swarmStatus === "paused") return;

        const currentAgent = agents[currentActiveIdx];
        const nextActiveIdx = (currentActiveIdx + 1) % agents.length;
        const targetAgent = agents[nextActiveIdx];

        setLastInteractedAgent(currentAgent);
        setActiveTelemetry({
          latencyMs: 400 + Math.floor(Math.random() * 300),
          billingUsd: 0.012 + Math.random() * 0.02,
          lastMessage: `Debate consensus round: ${currentAgent} dispatched update to ${targetAgent}`
        });

        // Set node styles
        setSwarmNodes(nodes =>
          nodes.map(node => ({
            ...node,
            className: node.id === currentAgent ? "active-streaming-node" : "",
            style: {
              ...node.style,
              borderColor: node.id === currentAgent ? "var(--accent)" : "var(--border-c)",
              boxShadow: node.id === currentAgent ? "0 0 15px var(--accent)" : "none"
            }
          }))
        );

        // Animate edge
        setSwarmEdges(edges =>
          edges.map(edge => ({
            ...edge,
            animated: edge.source === currentAgent,
            style: {
              ...edge.style,
              stroke: edge.source === currentAgent ? "var(--accent)" : "var(--border-c)",
              strokeWidth: edge.source === currentAgent ? 2.5 : 1.5
            }
          }))
        );

        currentActiveIdx = nextActiveIdx;
      }, 3000);
    }

    return () => {
      if (ws) ws.close();
      if (mockInterval) clearInterval(mockInterval);
    };
  }, [selectedSessionId, wsConnected, swarmStatus]);

  // Ledger Chain React Flow builder
  useEffect(() => {
    if (auditBlocks.length === 0) {
      setLedgerNodes([]);
      setLedgerEdges([]);
      return;
    }

    // Linear chain Layout
    const nodes = auditBlocks.map((block, i) => {
      const isTampered = !auditStatus.valid && block.id === auditStatus.tampered_id;
      return {
        id: `block-${block.id}`,
        data: {
          label: (
            <div className="flex flex-col text-[10px] text-left leading-relaxed">
              <span className="font-extrabold uppercase text-[9px]" style={{ color: isTampered ? "#f87171" : "var(--accent)" }}>
                Block #{block.id}
              </span>
              <span className="max-w-[130px] truncate font-bold t1">{block.event_type}</span>
              <span className="font-mono text-[8px] t3">Hash: {block.current_hash.slice(0, 10)}...</span>
            </div>
          )
        },
        position: { x: i * 220 + 20, y: 60 },
        style: {
          background: "var(--bg-card)",
          borderColor: isTampered ? "#ef4444" : "var(--border-c)",
          boxShadow: isTampered ? "0 0 20px rgba(239, 68, 68, 0.45)" : "none",
          borderWidth: isTampered ? "2px" : "1px",
          color: "var(--t1)",
          width: 170,
          borderRadius: "10px",
          padding: "8px 12px"
        }
      };
    });

    const edges = [];
    for (let i = 1; i < auditBlocks.length; i++) {
      const sourceId = `block-${auditBlocks[i - 1].id}`;
      const targetId = `block-${auditBlocks[i].id}`;
      const hasFailure = !auditStatus.valid && auditBlocks[i].id === auditStatus.tampered_id;
      edges.push({
        id: `edge-${sourceId}-${targetId}`,
        source: sourceId,
        target: targetId,
        animated: !hasFailure,
        style: {
          stroke: hasFailure ? "#ef4444" : "var(--accent)",
          strokeWidth: 2
        }
      });
    }

    setLedgerNodes(nodes);
    setLedgerEdges(edges);
  }, [auditBlocks, auditStatus]);

  // Simulate ledger tamper for visual test
  const simulateTamper = () => {
    setAuditStatus({
      valid: false,
      tampered_id: auditBlocks[1] ? auditBlocks[1].id : 1,
      merkle_root: "mock_tampered_merkle_root_001928"
    });
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto pr-2">
      {/* 1. Header Area */}
      <div className="flex justify-between items-center border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
        <div>
          <h1 className="text-xl font-black t1">{t.adminConsole}</h1>
          <p className="text-xs t3 mt-0.5">Enterprise isolation billing limits, WebSockets visual interceptor, and SOC2 cryptographic auditing.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              setLoadingTenants(true);
              fetchTenants();
              fetchLedger();
            }}
              className="quiet-button rounded-lg px-3 py-1.5 text-xs font-semibold"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* 2. Tenant & Billing Grid */}
      <Surface as="section" elevated className="flex flex-col gap-3 p-4">
        <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{t.billingPlans}</h2>
        {loadingTenants ? (
          <div className="text-center text-xs py-4 t3">Loading tenants...</div>
        ) : errorTenants ? (
          <div className="text-center text-xs py-4" style={{ color: "var(--danger)" }}>Error: {errorTenants}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tenants.map(tenant => (
              <Surface
                key={tenant.tenant_id}
                className="relative flex flex-col gap-3 p-4"
              >
                {/* Header */}
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs font-black t1">{tenant.tenant_id}</span>
                    <p className="mt-0.5 max-w-[150px] truncate font-mono text-[9px] t3">
                      Stripe: {tenant.stripe_subscription_id || "None"}
                    </p>
                  </div>
                  <StatusBadge tone={toneForStatus(tenant.status)}>
                    {tenant.status}
                  </StatusBadge>
                </div>

                {/* API Key Rotation */}
                <div className="flex flex-col gap-1 text-[10px]">
                  <span className="font-bold t3 uppercase tracking-[0.08em]">{t.apiKeyRotation}</span>
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      readOnly
                      value={rotatedKeyInfo[tenant.tenant_id] || tenant.api_key}
                      className="field-input min-w-0 flex-1 rounded px-2 py-1 font-mono text-[10px]"
                    />
                    <Button
                      onClick={() => handleRotateKey(tenant.tenant_id)}
                      className="px-2.5 py-1 text-[10px]"
                      title="Rotate Tenant API Key"
                    >
                      Rotate
                    </Button>
                  </div>
                  {rotatedKeyInfo[tenant.tenant_id] && (
                    <span className="text-[8px] font-bold" style={{ color: "var(--warning)" }}>Key rotated successfully in-memory.</span>
                  )}
                </div>

                {/* Usage meter */}
                <div className="flex flex-col gap-1 text-[10px] mt-1">
                  <div className="flex justify-between font-bold">
                    <span className="t3 uppercase tracking-[0.08em]">{t.realTimeUsage}</span>
                    <span className="font-mono t3">
                      {tenant.tokens_last_minute} / 5k tpm
                    </span>
                  </div>
                  <ProgressBar
                    value={(tenant.tokens_last_minute / 5000) * 100}
                    tone={tenant.tokens_last_minute >= 4000 ? "danger" : tenant.tokens_last_minute >= 2500 ? "warning" : "accent"}
                  />
                  <div className="mt-0.5 flex justify-between text-[8px] t3">
                    <span>Total: {tenant.total_tokens.toLocaleString()} tokens</span>
                    <span>Cost: ${tenant.total_cost_usd.toFixed(4)}</span>
                  </div>
                </div>

                {/* Simulation Control Overlay */}
                {tenant.tenant_id !== "admin_tenant" && (
                  <div className="flex gap-1 border-t pt-2.5 mt-1 border-dashed" style={{ borderColor: "var(--border-c)" }}>
                    <Button
                      onClick={() => handleUpdateSubscription(tenant.tenant_id, "active")}
                      variant="primary"
                      className="flex-1 py-1 text-[9px]"
                    >
                      Active
                    </Button>
                    <Button
                      onClick={() => handleUpdateSubscription(tenant.tenant_id, "frozen")}
                      variant="warning"
                      className="flex-1 py-1 text-[9px]"
                    >
                      Freeze
                    </Button>
                    <Button
                      onClick={() => handleUpdateSubscription(tenant.tenant_id, "canceled")}
                      variant="danger"
                      className="flex-1 py-1 text-[9px]"
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              </Surface>
            ))}
          </div>
        )}
      </Surface>

      {/* 3. Swarm Live Interceptor & Ledger Visualizer Row */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Swarm Live Interceptor Canvas */}
        <Surface as="section" elevated className="relative flex min-h-[460px] flex-col gap-3 p-4 lg:col-span-7">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{t.liveInterceptor}</h2>
              <p className="text-[10px] t3 mt-0.5">Session: {selectedSessionId}</p>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge tone={wsConnected ? "success" : "warning"}>
                {wsConnected ? "WEBSOCKET LIVE" : "OFFLINE SIMULATION"}
              </StatusBadge>
            </div>
          </div>

          {/* React Flow Swarm Canvas */}
          <div className="flow-canvas relative min-h-[280px] flex-1 overflow-hidden rounded-lg border" style={{ borderColor: "var(--border-c)" }}>
            <ReactFlow
              nodes={swarmNodes}
              edges={swarmEdges}
              onNodesChange={onSwarmNodesChange}
              onEdgesChange={onSwarmEdgesChange}
              fitView
              minZoom={0.2}
              maxZoom={1.5}
            >
              <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--grid)" />
            </ReactFlow>

            {/* Float Telemetry Panel overlay */}
            <Surface className="absolute bottom-3 left-3 z-10 flex max-w-[280px] flex-col gap-1 p-2.5 text-[9px]">
              <div className="flex justify-between font-bold t2">
                <span>Last Node: <strong style={{ color: "var(--accent)" }}>{lastInteractedAgent || "None"}</strong></span>
                <span>Latency: <strong style={{ color: "var(--accent)" }}>{activeTelemetry.latencyMs}ms</strong></span>
              </div>
              <p className="mt-0.5 truncate t3">{activeTelemetry.lastMessage}</p>
              <div className="mt-1 flex items-center justify-between border-t pt-1 font-mono t3" style={{ borderColor: "var(--border-c)" }}>
                <span>Markup pricing applied</span>
                <span className="font-bold" style={{ color: "var(--success)" }}>${activeTelemetry.billingUsd.toFixed(4)} USD</span>
              </div>
            </Surface>
          </div>

          {/* Action Row */}
          <div className="flex gap-2">
            <Button
              onClick={handlePauseSwarm}
              variant={swarmStatus === "paused" ? "warning" : "quiet"}
              className="flex-1"
            >
              {t.pauseSwarm}
            </Button>
            <Button
              onClick={handleResumeSwarm}
              variant={swarmStatus === "running" ? "primary" : "quiet"}
              className="flex-1"
            >
              {t.resumeSwarm}
            </Button>
            <Button
              onClick={() => setShowHijackInput(!showHijackInput)}
              className="flex-1"
            >
              {t.hijackInput}
            </Button>
          </div>

          {/* Hijack Text Box Popup overlay */}
          {showHijackInput && (
            <Surface className="absolute inset-x-4 bottom-16 z-20 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between border-b pb-1.5" style={{ borderColor: "var(--border-c)" }}>
                <span className="text-[10px] font-bold t2">Inject Human-In-The-Loop Hijacked Input</span>
                <Button onClick={() => setShowHijackInput(false)} className="px-2 py-1 text-[10px]">Close</Button>
              </div>
              <textarea
                value={hijackText}
                onChange={e => setHijackText(e.target.value)}
                placeholder="Type response mock value or direct instructions to bypass native tool execution..."
                className="field-input h-16 resize-none rounded p-2 font-mono text-xs"
              />
              <Button
                onClick={handleHijackInput}
                variant="primary"
                className="w-full"
              >
                Submit Hijacked Input
              </Button>
            </Surface>
          )}
        </Surface>

        {/* Ledger Validation Visualizer */}
        <Surface as="section" elevated className="relative flex min-h-[460px] flex-col gap-3 p-4 lg:col-span-5">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{t.ledgerVisualizer}</h2>
              <p className="text-[9px] t3 mt-0.5">SOC2 SHA-256 AuditLedger</p>
            </div>
            <StatusBadge tone={auditStatus.valid ? "success" : "danger"}>
              {auditStatus.valid ? "HEALTHY" : "TAMPERED"}
            </StatusBadge>
          </div>

          {/* Validation Status Card */}
          <Surface className="flex flex-col gap-1 p-3 text-[10px]">
            <div className="flex justify-between">
              <span className="t3">Merkle Root:</span>
              <span className="max-w-[170px] truncate font-mono t2" title={auditStatus.merkle_root}>
                {auditStatus.merkle_root || "0x00000000000000000000"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="t3">Block Validation Count:</span>
              <span className="font-mono font-bold t2">{auditBlocks.length} blocks verified</span>
            </div>
            {auditStatus.tampered_id !== null && (
              <div className="mt-1.5 flex items-center gap-1.5 border-t pt-2 font-bold" style={{ borderColor: "color-mix(in srgb, var(--danger) 28%, transparent)", color: "var(--danger)" }}>
                <span className="text-[12px]">!</span>
                <span>Audit breach detected at Block #{auditStatus.tampered_id}! Block hash chain mismatch.</span>
              </div>
            )}
          </Surface>

          {/* React Flow Ledger chain */}
          <div className="flow-canvas relative min-h-[220px] flex-1 overflow-hidden rounded-lg border" style={{ borderColor: "var(--border-c)" }}>
            <ReactFlow
              nodes={ledgerNodes}
              edges={ledgerEdges}
              onNodesChange={onLedgerNodesChange}
              onEdgesChange={onLedgerEdgesChange}
              fitView
              minZoom={0.15}
              maxZoom={1.3}
            >
              <Background variant={BackgroundVariant.Dots} gap={15} size={1} color="var(--grid)" />
            </ReactFlow>
          </div>

          {/* Action Row */}
          <div className="flex gap-2">
            <Button
              onClick={fetchLedger}
              disabled={checkingLedger}
              className="flex-1"
            >
              {checkingLedger ? "Verifying..." : "Verify Chain"}
            </Button>
            <Button
              onClick={simulateTamper}
              variant="danger"
              className="flex-1"
            >
              Simulate Tamper
            </Button>
          </div>
        </Surface>
      </div>
    </div>
  );
}
