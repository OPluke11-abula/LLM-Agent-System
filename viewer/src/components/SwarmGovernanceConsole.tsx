import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, ProgressBar, StatusBadge, Surface, toneForStatus } from "./ui/primitives";
import type { Lang } from "../types";

type Tone = "success" | "warning" | "danger";

export type SwarmReplayEvent = {
  id: string;
  step: number;
  node_id: string;
  source?: string;
  target?: string;
  status: string;
  label: string;
  latency_ms?: number;
};

type SwarmNode = {
  id: string;
  role: string;
  status: string;
  taskLoad: number;
};

type HealthLog = {
  id: string;
  timestamp: string;
  nodeId: string;
  message: string;
  tone: Tone;
};

type SwarmSession = {
  id: string;
  status: string;
  completed: number;
  total: number;
  checkpoints: Array<{ id: string; label: string; done: boolean }>;
};

type PeerNode = {
  id: string;
  latencyMs: number;
  mtls: boolean;
  status: string;
};

type BillingStatus = {
  remainingCredits: number;
  spendUsd: number;
  trend: number;
  policy: BillingPolicy;
};

type BillingPolicy = "strict_quota" | "auto_downscale";

type AuditProof = {
  eventId: string;
  merkleProof: string[];
  zkKeys: string[];
  root: string;
};

type ProofValidation = {
  valid: boolean;
  message: string;
};

type GovernanceCopy = {
  operationsTitle: string;
  operationsSubtitle: string;
  refresh: string;
  nodeRegistry: string;
  collapse: string;
  expand: string;
  scaleUp: string;
  scaleDown: string;
  load: string;
  heartbeatLog: string;
  sessions: string;
  completed: string;
  pending: string;
  forceResume: string;
  resuming: string;
  peers: string;
  latency: string;
  locked: string;
  unlocked: string;
  billing: string;
  remainingCredits: string;
  spendTrend: string;
  policy: string;
  strictQuota: string;
  autoDownscale: string;
  proofInspector: string;
  eventId: string;
  loadProof: string;
  verifyProof: string;
  blockHashPlaceholder: string;
  merkleProof: string;
  zkKeys: string;
  noData: string;
  offline: string;
  loaded: string;
  actionFailed: string;
  replay: string;
  play: string;
  pause: string;
  step: string;
  timeline: string;
};

const GOVERNANCE_COPY: Record<Lang, GovernanceCopy> = {
  zh: {
    operationsTitle: "Swarm Operations & Cryptographic Governance",
    operationsSubtitle: "節點彈性、會話恢復、P2P mesh、預算策略與審計 proof 集中操作。",
    refresh: "重新整理",
    nodeRegistry: "Active Node Registry",
    collapse: "收合",
    expand: "展開",
    scaleUp: "擴容",
    scaleDown: "縮容",
    load: "負載",
    heartbeatLog: "Heartbeat & Failover Log",
    sessions: "Active Sessions",
    completed: "完成",
    pending: "待處理",
    forceResume: "Force Resume",
    resuming: "恢復中",
    peers: "P2P Mesh Peers",
    latency: "延遲",
    locked: "mTLS locked",
    unlocked: "mTLS open",
    billing: "Billing Budget",
    remainingCredits: "剩餘額度",
    spendTrend: "支出趨勢",
    policy: "資源策略",
    strictQuota: "Strict Quota Limit",
    autoDownscale: "Auto-Downscale",
    proofInspector: "Merkle & ZK Proof Inspector",
    eventId: "Event ID",
    loadProof: "載入 proof",
    verifyProof: "Verify Cryptographic Proof",
    blockHashPlaceholder: "貼上 block hash...",
    merkleProof: "Merkle proof",
    zkKeys: "ZK keys",
    noData: "無資料",
    offline: "使用本地 fallback snapshot。",
    loaded: "治理資料已載入。",
    actionFailed: "操作失敗",
    replay: "Replay",
    play: "播放",
    pause: "暫停",
    step: "下一步",
    timeline: "時間軸",
  },
  en: {
    operationsTitle: "Swarm Operations & Cryptographic Governance",
    operationsSubtitle: "Elastic nodes, session recovery, P2P mesh, budget policy, and audit proofs in one operator surface.",
    refresh: "Refresh",
    nodeRegistry: "Active Node Registry",
    collapse: "Collapse",
    expand: "Expand",
    scaleUp: "Scale Up",
    scaleDown: "Scale Down",
    load: "Load",
    heartbeatLog: "Heartbeat & Failover Log",
    sessions: "Active Sessions",
    completed: "Completed",
    pending: "Pending",
    forceResume: "Force Resume",
    resuming: "Resuming",
    peers: "P2P Mesh Peers",
    latency: "Latency",
    locked: "mTLS locked",
    unlocked: "mTLS open",
    billing: "Billing Budget",
    remainingCredits: "Remaining credits",
    spendTrend: "Spend trend",
    policy: "Resource policy",
    strictQuota: "Strict Quota Limit",
    autoDownscale: "Auto-Downscale",
    proofInspector: "Merkle & ZK Proof Inspector",
    eventId: "Event ID",
    loadProof: "Load proof",
    verifyProof: "Verify Cryptographic Proof",
    blockHashPlaceholder: "Paste block hash...",
    merkleProof: "Merkle proof",
    zkKeys: "ZK keys",
    noData: "No data",
    offline: "Using local fallback snapshot.",
    loaded: "Governance data loaded.",
    actionFailed: "Action failed",
    replay: "Replay",
    play: "Play",
    pause: "Pause",
    step: "Step",
    timeline: "Timeline",
  },
  ja: {
    operationsTitle: "Swarm Operations & Cryptographic Governance",
    operationsSubtitle: "ノード伸縮、セッション復旧、P2P mesh、予算ポリシー、監査 proof を一つの操作面に統合します。",
    refresh: "更新",
    nodeRegistry: "Active Node Registry",
    collapse: "折りたたむ",
    expand: "展開",
    scaleUp: "スケールアップ",
    scaleDown: "スケールダウン",
    load: "負荷",
    heartbeatLog: "Heartbeat & Failover Log",
    sessions: "Active Sessions",
    completed: "完了",
    pending: "未完了",
    forceResume: "Force Resume",
    resuming: "復旧中",
    peers: "P2P Mesh Peers",
    latency: "レイテンシ",
    locked: "mTLS locked",
    unlocked: "mTLS open",
    billing: "Billing Budget",
    remainingCredits: "残りクレジット",
    spendTrend: "支出トレンド",
    policy: "リソースポリシー",
    strictQuota: "Strict Quota Limit",
    autoDownscale: "Auto-Downscale",
    proofInspector: "Merkle & ZK Proof Inspector",
    eventId: "Event ID",
    loadProof: "proof 読込",
    verifyProof: "Verify Cryptographic Proof",
    blockHashPlaceholder: "block hash を貼り付け...",
    merkleProof: "Merkle proof",
    zkKeys: "ZK keys",
    noData: "データなし",
    offline: "ローカル fallback snapshot を使用中。",
    loaded: "Governance data loaded.",
    actionFailed: "操作失敗",
    replay: "Replay",
    play: "再生",
    pause: "一時停止",
    step: "次へ",
    timeline: "タイムライン",
  },
  fr: {
    operationsTitle: "Swarm Operations & Cryptographic Governance",
    operationsSubtitle: "Noeuds élastiques, reprise de session, mesh P2P, politique budgétaire et preuves d'audit dans une surface opérateur.",
    refresh: "Actualiser",
    nodeRegistry: "Active Node Registry",
    collapse: "Réduire",
    expand: "Étendre",
    scaleUp: "Scale Up",
    scaleDown: "Scale Down",
    load: "Charge",
    heartbeatLog: "Heartbeat & Failover Log",
    sessions: "Active Sessions",
    completed: "Terminés",
    pending: "En attente",
    forceResume: "Force Resume",
    resuming: "Reprise",
    peers: "P2P Mesh Peers",
    latency: "Latence",
    locked: "mTLS locked",
    unlocked: "mTLS open",
    billing: "Billing Budget",
    remainingCredits: "Crédits restants",
    spendTrend: "Tendance dépense",
    policy: "Politique ressource",
    strictQuota: "Strict Quota Limit",
    autoDownscale: "Auto-Downscale",
    proofInspector: "Merkle & ZK Proof Inspector",
    eventId: "Event ID",
    loadProof: "Charger proof",
    verifyProof: "Verify Cryptographic Proof",
    blockHashPlaceholder: "Coller block hash...",
    merkleProof: "Merkle proof",
    zkKeys: "ZK keys",
    noData: "Aucune donnée",
    offline: "Snapshot local fallback utilisé.",
    loaded: "Données de gouvernance chargées.",
    actionFailed: "Action échouée",
    replay: "Replay",
    play: "Lire",
    pause: "Pause",
    step: "Étape",
    timeline: "Timeline",
  },
};

const fallbackNodes: SwarmNode[] = [
  { id: "local-ceo-01", role: "CEO", status: "busy", taskLoad: 72 },
  { id: "local-dev-02", role: "Developer", status: "busy", taskLoad: 64 },
  { id: "local-qa-03", role: "QA", status: "idle", taskLoad: 18 },
  { id: "local-cfo-04", role: "CFO", status: "idle", taskLoad: 31 },
];

const fallbackHealth: HealthLog[] = [
  { id: "health-1", timestamp: "09:42:11", nodeId: "local-dev-02", message: "Heartbeat recovered after 1 retry.", tone: "success" },
  { id: "health-2", timestamp: "09:40:28", nodeId: "edge-qa-07", message: "Heartbeat timeout, failover candidate queued.", tone: "warning" },
  { id: "health-3", timestamp: "09:38:03", nodeId: "local-cfo-04", message: "Resource policy applied: auto-downscale accepted.", tone: "success" },
];

const fallbackSessions: SwarmSession[] = [
  {
    id: "default",
    status: "running",
    completed: 3,
    total: 4,
    checkpoints: [
      { id: "initialize", label: "initialize", done: true },
      { id: "execute", label: "execute", done: true },
      { id: "audit", label: "audit", done: true },
      { id: "finalize", label: "finalize", done: false },
    ],
  },
  {
    id: "recovery-ops-184",
    status: "pending",
    completed: 2,
    total: 4,
    checkpoints: [
      { id: "initialize", label: "initialize", done: true },
      { id: "execute", label: "execute", done: true },
      { id: "audit", label: "audit", done: false },
      { id: "finalize", label: "finalize", done: false },
    ],
  },
];

const fallbackPeers: PeerNode[] = [
  { id: "peer-tpe-01", latencyMs: 24, mtls: true, status: "connected" },
  { id: "peer-nrt-02", latencyMs: 58, mtls: true, status: "connected" },
  { id: "peer-sjc-03", latencyMs: 91, mtls: false, status: "degraded" },
];

const fallbackBilling: BillingStatus = {
  remainingCredits: 1842,
  spendUsd: 42.18,
  trend: 12,
  policy: "auto_downscale",
};

const fallbackReplay: SwarmReplayEvent[] = [
  { id: "r-1", step: 0, node_id: "CEO", target: "Developer", status: "running", label: "initialize", latency_ms: 210 },
  { id: "r-2", step: 1, node_id: "Developer", target: "QA", status: "running", label: "execute", latency_ms: 360 },
  { id: "r-3", step: 2, node_id: "QA", target: "CFO", status: "review", label: "audit", latency_ms: 440 },
  { id: "r-4", step: 3, node_id: "CFO", target: "CEO", status: "completed", label: "finalize", latency_ms: 180 },
];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function asNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function asBoolean(value: unknown, fallback = false) {
  return typeof value === "boolean" ? value : fallback;
}

function readArray(value: unknown, keys: string[]) {
  if (Array.isArray(value)) return value;
  const record = asRecord(value);
  for (const key of keys) {
    if (Array.isArray(record[key])) return record[key] as unknown[];
  }
  return [];
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      "x-api-key": "key-admin",
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function mapNodes(raw: unknown): SwarmNode[] {
  const items = readArray(raw, ["nodes", "data"]);
  return items.map((item, index) => {
    const record = asRecord(item);
    return {
      id: asString(record.id ?? record.node_id, `node-${index + 1}`),
      role: asString(record.role ?? record.service_role, "worker"),
      status: asString(record.status, "idle"),
      taskLoad: asNumber(record.task_load ?? record.load ?? record.current_task_load, 0),
    };
  });
}

function mapHealth(raw: unknown): HealthLog[] {
  const items = readArray(raw, ["logs", "events", "failovers"]);
  return items.map((item, index) => {
    const record = asRecord(item);
    const severity = asString(record.severity ?? record.status, "success").toLowerCase();
    return {
      id: asString(record.id, `health-${index + 1}`),
      timestamp: asString(record.timestamp ?? record.time, "--:--:--"),
      nodeId: asString(record.node_id ?? record.nodeId, "node"),
      message: asString(record.message ?? record.event, "Heartbeat observed."),
      tone: severity.includes("fail") || severity.includes("timeout") || severity.includes("warn") ? "warning" : "success",
    };
  });
}

function mapSessions(raw: unknown): SwarmSession[] {
  const items = readArray(raw, ["sessions", "data"]);
  return items.map((item, index) => {
    const record = asRecord(item);
    const checkpointsRaw = readArray(record.checkpoints, ["checkpoints"]);
    const checkpoints = checkpointsRaw.length > 0
      ? checkpointsRaw.map((checkpoint, checkpointIndex) => {
        const checkpointRecord = asRecord(checkpoint);
        const id = asString(checkpointRecord.id ?? checkpointRecord.name, `checkpoint-${checkpointIndex + 1}`);
        return {
          id,
          label: asString(checkpointRecord.label ?? checkpointRecord.name, id),
          done: asBoolean(checkpointRecord.done ?? checkpointRecord.completed, false),
        };
      })
      : ["initialize", "execute", "audit", "finalize"].map(label => ({ id: label, label, done: false }));
    const completed = checkpoints.filter(checkpoint => checkpoint.done).length;
    return {
      id: asString(record.id ?? record.session_id, `session-${index + 1}`),
      status: asString(record.status, "pending"),
      completed: asNumber(record.completed, completed),
      total: asNumber(record.total, checkpoints.length),
      checkpoints,
    };
  });
}

function mapPeers(raw: unknown): PeerNode[] {
  const items = readArray(raw, ["peers", "nodes", "data"]);
  return items.map((item, index) => {
    const record = asRecord(item);
    return {
      id: asString(record.id ?? record.peer_id, `peer-${index + 1}`),
      latencyMs: asNumber(record.latency_ms ?? record.latency, 0),
      mtls: asBoolean(record.mtls ?? record.secure ?? record.mtls_enabled, false),
      status: asString(record.status, "connected"),
    };
  });
}

function mapBilling(raw: unknown): BillingStatus {
  const record = asRecord(raw);
  const data = Object.keys(asRecord(record.data)).length > 0 ? asRecord(record.data) : record;
  const policy = asString(data.policy, fallbackBilling.policy) === "strict_quota" ? "strict_quota" : "auto_downscale";
  return {
    remainingCredits: asNumber(data.remaining_credits ?? data.remainingCredits, fallbackBilling.remainingCredits),
    spendUsd: asNumber(data.spend_usd ?? data.spendUsd, fallbackBilling.spendUsd),
    trend: asNumber(data.trend ?? data.spend_trend, fallbackBilling.trend),
    policy,
  };
}

function mapReplay(raw: unknown): SwarmReplayEvent[] {
  const items = readArray(raw, ["events", "replay", "timeline"]);
  return items.map((item, index) => {
    const record = asRecord(item);
    return {
      id: asString(record.id ?? record.event_id, `replay-${index + 1}`),
      step: asNumber(record.step, index),
      node_id: asString(record.node_id ?? record.agent ?? record.source, "CEO"),
      source: asString(record.source, asString(record.node_id, "")) || undefined,
      target: asString(record.target, "") || undefined,
      status: asString(record.status, "running"),
      label: asString(record.label ?? record.event ?? record.title, `step ${index + 1}`),
      latency_ms: asNumber(record.latency_ms ?? record.duration_ms, 0),
    };
  });
}

function groupNodesByRole(nodes: SwarmNode[]) {
  return nodes.reduce<Record<string, SwarmNode[]>>((groups, node) => {
    groups[node.role] = groups[node.role] ?? [];
    groups[node.role].push(node);
    return groups;
  }, {});
}

export function ReplayPlaybackWidget({
  sessionId,
  lang,
  onReplayEvent,
}: {
  sessionId: string;
  lang: Lang;
  onReplayEvent: (event: SwarmReplayEvent) => void;
}) {
  const copy = GOVERNANCE_COPY[lang];
  const [events, setEvents] = useState<SwarmReplayEvent[]>(fallbackReplay);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchJson<unknown>(`http://localhost:8000/v1/swarm/replays/${sessionId}`)
      .then(raw => {
        if (cancelled) return;
        const nextEvents = mapReplay(raw);
        setEvents(nextEvents.length > 0 ? nextEvents : fallbackReplay);
        setIndex(0);
      })
      .catch(() => {
        if (!cancelled) setEvents(fallbackReplay);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!playing || events.length === 0) return undefined;
    const timer = window.setInterval(() => {
      setIndex(current => {
        const next = current >= events.length - 1 ? 0 : current + 1;
        onReplayEvent(events[next]);
        return next;
      });
    }, 1400);
    return () => window.clearInterval(timer);
  }, [events, onReplayEvent, playing]);

  const current = events[index] ?? fallbackReplay[0];

  function stepForward() {
    const next = index >= events.length - 1 ? 0 : index + 1;
    setIndex(next);
    onReplayEvent(events[next]);
  }

  return (
    <Surface className="absolute bottom-3 right-3 z-10 flex w-[320px] max-w-[calc(100%-1.5rem)] flex-col gap-2 p-2.5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[9px] font-black uppercase tracking-[0.14em] t2">{copy.replay}</p>
          <p className="max-w-[180px] truncate text-[10px] t3">{current.label}</p>
        </div>
        <StatusBadge tone={toneForStatus(current.status)}>{current.status}</StatusBadge>
      </div>
      <div className="flex items-center gap-1.5">
        <Button onClick={() => setPlaying(value => !value)} className="px-2 py-1 text-[10px]">
          {playing ? copy.pause : copy.play}
        </Button>
        <Button onClick={stepForward} variant="quiet" className="px-2 py-1 text-[10px]">
          {copy.step}
        </Button>
        <label className="sr-only" htmlFor="swarm-replay-slider">{copy.timeline}</label>
        <input
          id="swarm-replay-slider"
          type="range"
          min={0}
          max={Math.max(0, events.length - 1)}
          value={index}
          onChange={event => {
            const nextIndex = Number(event.target.value);
            setIndex(nextIndex);
            onReplayEvent(events[nextIndex]);
          }}
          className="min-w-0 flex-1 accent-[var(--accent)]"
        />
        <span className="font-mono text-[10px] t3">{index + 1}/{events.length}</span>
      </div>
    </Surface>
  );
}

export function SwarmGovernanceConsole({
  lang,
  onStatus,
}: {
  lang: Lang;
  onStatus: (message: string, tone?: Tone) => void;
}) {
  const copy = GOVERNANCE_COPY[lang];
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [nodes, setNodes] = useState<SwarmNode[]>(fallbackNodes);
  const [healthLogs, setHealthLogs] = useState<HealthLog[]>(fallbackHealth);
  const [sessions, setSessions] = useState<SwarmSession[]>(fallbackSessions);
  const [peers, setPeers] = useState<PeerNode[]>(fallbackPeers);
  const [billing, setBilling] = useState<BillingStatus>(fallbackBilling);
  const [loading, setLoading] = useState(false);
  const [resumeLoading, setResumeLoading] = useState<string | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [proofEventId, setProofEventId] = useState("event-001");
  const [proof, setProof] = useState<AuditProof | null>(null);
  const [proofLoading, setProofLoading] = useState(false);
  const [blockHash, setBlockHash] = useState("");
  const [validation, setValidation] = useState<ProofValidation | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);

  const groupedNodes = useMemo(() => groupNodesByRole(nodes), [nodes]);

  const loadGovernanceData = useCallback(async () => {
    setLoading(true);
    const [nodeResult, healthResult, sessionResult, peerResult, billingResult] = await Promise.allSettled([
      fetchJson<unknown>("http://localhost:8000/v1/swarm/nodes"),
      fetchJson<unknown>("http://localhost:8000/v1/swarm/health"),
      fetchJson<unknown>("http://localhost:8000/v1/swarm/sessions"),
      fetchJson<unknown>("http://localhost:8000/v1/swarm/peers"),
      fetchJson<unknown>("http://localhost:8000/v1/swarm/billing/status"),
    ]);

    let usedFallback = false;
    if (nodeResult.status === "fulfilled") {
      const nextNodes = mapNodes(nodeResult.value);
      setNodes(nextNodes.length > 0 ? nextNodes : fallbackNodes);
    } else {
      usedFallback = true;
      setNodes(fallbackNodes);
    }
    if (healthResult.status === "fulfilled") {
      const nextLogs = mapHealth(healthResult.value);
      setHealthLogs(nextLogs.length > 0 ? nextLogs : fallbackHealth);
    } else {
      usedFallback = true;
      setHealthLogs(fallbackHealth);
    }
    if (sessionResult.status === "fulfilled") {
      const nextSessions = mapSessions(sessionResult.value);
      setSessions(nextSessions.length > 0 ? nextSessions : fallbackSessions);
    } else {
      usedFallback = true;
      setSessions(fallbackSessions);
    }
    if (peerResult.status === "fulfilled") {
      const nextPeers = mapPeers(peerResult.value);
      setPeers(nextPeers.length > 0 ? nextPeers : fallbackPeers);
    } else {
      usedFallback = true;
      setPeers(fallbackPeers);
    }
    if (billingResult.status === "fulfilled") {
      setBilling(mapBilling(billingResult.value));
    } else {
      usedFallback = true;
      setBilling(fallbackBilling);
    }
    setLoading(false);
    onStatus(usedFallback ? copy.offline : copy.loaded, usedFallback ? "warning" : "success");
  }, [copy.loaded, copy.offline, onStatus]);

  useEffect(() => {
    void loadGovernanceData();
  }, [loadGovernanceData]);

  async function scaleRole(role: string, direction: "up" | "down") {
    try {
      await fetchJson<unknown>("http://localhost:8000/v1/swarm/scale", {
        method: "POST",
        body: JSON.stringify({ role, direction }),
      });
      onStatus(`${role}: ${direction === "up" ? copy.scaleUp : copy.scaleDown}`);
      void loadGovernanceData();
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    }
  }

  async function resumeSession(sessionId: string) {
    setResumeLoading(sessionId);
    try {
      await fetchJson<unknown>("http://localhost:8000/v1/swarm/sessions/resume", {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId }),
      });
      onStatus(`${sessionId}: ${copy.forceResume}`);
      void loadGovernanceData();
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    } finally {
      setResumeLoading(null);
    }
  }

  async function updatePolicy(policy: BillingPolicy) {
    setPolicyLoading(true);
    setBilling(current => ({ ...current, policy }));
    try {
      await fetchJson<unknown>("http://localhost:8000/v1/swarm/billing/policy", {
        method: "POST",
        body: JSON.stringify({ policy }),
      });
      onStatus(`${copy.policy}: ${policy === "strict_quota" ? copy.strictQuota : copy.autoDownscale}`);
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    } finally {
      setPolicyLoading(false);
    }
  }

  async function loadProof() {
    if (!proofEventId.trim()) return;
    setProofLoading(true);
    setProof(null);
    try {
      const raw = await fetchJson<unknown>(`http://localhost:8000/v1/audit/proof/${encodeURIComponent(proofEventId.trim())}`);
      const record = asRecord(raw);
      const data = Object.keys(asRecord(record.data)).length > 0 ? asRecord(record.data) : record;
      setProof({
        eventId: asString(data.event_id ?? data.eventId, proofEventId),
        merkleProof: readArray(data.merkle_proof ?? data.merkleProof, ["proof"]).map(item => String(item)),
        zkKeys: readArray(data.zk_keys ?? data.zkKeys, ["keys"]).map(item => String(item)),
        root: asString(data.root ?? data.merkle_root, "0x00000000000000000000"),
      });
    } catch (error) {
      setProof({
        eventId: proofEventId,
        merkleProof: ["fallback-sibling-left", "fallback-sibling-right"],
        zkKeys: ["local-verifier-key", "session-public-input"],
        root: "fallback-root",
      });
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "warning");
    } finally {
      setProofLoading(false);
    }
  }

  async function verifyProof() {
    if (!blockHash.trim()) return;
    setValidationLoading(true);
    setValidation(null);
    try {
      const raw = await fetchJson<unknown>("http://localhost:8000/v1/audit/verify-proof", {
        method: "POST",
        body: JSON.stringify({ block_hash: blockHash.trim(), event_id: proofEventId.trim() }),
      });
      const record = asRecord(raw);
      const valid = asBoolean(record.valid ?? record.ok, false);
      setValidation({
        valid,
        message: asString(record.message, valid ? "Proof verified." : "Proof rejected."),
      });
    } catch (error) {
      setValidation({ valid: false, message: error instanceof Error ? error.message : String(error) });
    } finally {
      setValidationLoading(false);
    }
  }

  return (
    <Surface as="section" elevated className="flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{copy.operationsTitle}</h2>
          <p className="mt-1 max-w-3xl text-xs t3">{copy.operationsSubtitle}</p>
        </div>
        <Button onClick={loadGovernanceData} disabled={loading} variant="quiet">
          {loading ? `${copy.refresh}...` : copy.refresh}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <Surface className="flex flex-col gap-3 p-3 xl:col-span-4">
          <div className="flex items-center justify-between">
            <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.nodeRegistry}</h3>
            <Button onClick={() => setDrawerOpen(value => !value)} className="px-2 py-1 text-[10px]">
              {drawerOpen ? copy.collapse : copy.expand}
            </Button>
          </div>
          {drawerOpen && (
            <div className="flex max-h-[310px] flex-col gap-3 overflow-y-auto pr-1">
              {Object.entries(groupedNodes).map(([role, roleNodes]) => (
                <div key={role} className="rounded-lg border p-2" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-[10px] font-bold uppercase tracking-[0.12em] t1">{role}</span>
                    <div className="flex gap-1">
                      <Button onClick={() => scaleRole(role, "down")} title={copy.scaleDown} className="h-7 w-7 px-0 py-0">-</Button>
                      <Button onClick={() => scaleRole(role, "up")} title={copy.scaleUp} variant="primary" className="h-7 w-7 px-0 py-0">+</Button>
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    {roleNodes.map(node => (
                      <div key={node.id} className="grid grid-cols-[1fr_auto] gap-2 text-[10px]">
                        <div className="min-w-0">
                          <p className="truncate font-mono font-semibold t2">{node.id}</p>
                          <ProgressBar value={node.taskLoad} tone={node.taskLoad > 72 ? "warning" : "accent"} className="mt-1" />
                        </div>
                        <div className="flex flex-col items-end gap-1">
                          <StatusBadge tone={toneForStatus(node.status)}>{node.status}</StatusBadge>
                          <span className="font-mono t3">{copy.load} {node.taskLoad}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Surface>

        <Surface className="flex flex-col gap-3 p-3 xl:col-span-4">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.sessions}</h3>
          <div className="grid grid-cols-1 gap-3">
            {sessions.map(session => (
              <div key={session.id} className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs font-semibold t1">{session.id}</p>
                    <p className="mt-1 text-[10px] t3">{copy.completed} {session.completed} / {session.total}</p>
                  </div>
                  <StatusBadge tone={toneForStatus(session.status)}>{session.status}</StatusBadge>
                </div>
                <div className="mt-3 grid grid-cols-4 gap-1.5">
                  {session.checkpoints.map(checkpoint => (
                    <div
                      key={checkpoint.id}
                      className="rounded border px-1.5 py-1 text-center text-[9px] font-semibold"
                      style={{
                        borderColor: checkpoint.done ? "color-mix(in srgb, var(--success) 36%, transparent)" : "var(--border-c)",
                        color: checkpoint.done ? "var(--success)" : "var(--t3)",
                        background: checkpoint.done ? "var(--success-bg)" : "var(--bg-muted)",
                      }}
                    >
                      {checkpoint.label}
                    </div>
                  ))}
                </div>
                <Button
                  onClick={() => resumeSession(session.id)}
                  disabled={resumeLoading === session.id}
                  variant="primary"
                  className="mt-3 w-full"
                >
                  {resumeLoading === session.id ? copy.resuming : copy.forceResume}
                </Button>
              </div>
            ))}
          </div>
        </Surface>

        <Surface className="flex flex-col gap-3 p-3 xl:col-span-4">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.heartbeatLog}</h3>
          <div className="min-h-[132px] rounded-lg border p-3 font-mono text-[10px]" style={{ borderColor: "var(--border-c)", background: "color-mix(in srgb, var(--bg-base) 74%, var(--bg-card))" }}>
            {healthLogs.map(log => (
              <div key={log.id} className="mb-2 grid grid-cols-[58px_1fr] gap-2 last:mb-0">
                <span className="t3">{log.timestamp}</span>
                <span style={{ color: log.tone === "warning" ? "var(--warning)" : "var(--t2)" }}>
                  [{log.nodeId}] {log.message}
                </span>
              </div>
            ))}
          </div>

          <h3 className="mt-1 text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.peers}</h3>
          <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--border-c)" }}>
            {peers.map(peer => (
              <div key={peer.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-2 border-b px-3 py-2 text-[10px] last:border-b-0" style={{ borderColor: "var(--border-c)" }}>
                <div className="min-w-0">
                  <p className="truncate font-mono font-semibold t2">{peer.id}</p>
                  <p className="t3">{peer.status}</p>
                </div>
                <span className="flex items-center gap-1.5 font-mono t2">
                  <span className="h-2 w-2 rounded-full" style={{ background: peer.latencyMs < 50 ? "var(--success)" : "var(--warning)" }} />
                  {peer.latencyMs}ms
                </span>
                <StatusBadge tone={peer.mtls ? "success" : "warning"}>{peer.mtls ? copy.locked : copy.unlocked}</StatusBadge>
              </div>
            ))}
          </div>
        </Surface>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Surface className="flex flex-col gap-3 p-3">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.billing}</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}>
              <p className="text-xl font-semibold t1">{billing.remainingCredits.toLocaleString()}</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] t3">{copy.remainingCredits}</p>
            </div>
            <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}>
              <p className="text-xl font-semibold t1">${billing.spendUsd.toFixed(2)}</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] t3">{copy.spendTrend} +{billing.trend}%</p>
            </div>
          </div>
          <label className="text-[10px] font-bold uppercase tracking-[0.12em] t3" htmlFor="billing-policy-select">
            {copy.policy}
          </label>
          <select
            id="billing-policy-select"
            value={billing.policy}
            onChange={event => updatePolicy(event.target.value as BillingPolicy)}
            disabled={policyLoading}
            className="field-input rounded-lg px-3 py-2 text-xs"
          >
            <option value="strict_quota">{copy.strictQuota}</option>
            <option value="auto_downscale">{copy.autoDownscale}</option>
          </select>
        </Surface>

        <Surface className="flex flex-col gap-3 p-3">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.proofInspector}</h3>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
            <label className="sr-only" htmlFor="audit-proof-event">{copy.eventId}</label>
            <input
              id="audit-proof-event"
              value={proofEventId}
              onChange={event => setProofEventId(event.target.value)}
              className="field-input rounded-lg px-3 py-2 font-mono text-xs"
              placeholder={copy.eventId}
            />
            <Button onClick={loadProof} disabled={proofLoading} variant="primary">
              {proofLoading ? `${copy.loadProof}...` : copy.loadProof}
            </Button>
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
            <label className="sr-only" htmlFor="audit-proof-hash">{copy.verifyProof}</label>
            <input
              id="audit-proof-hash"
              value={blockHash}
              onChange={event => setBlockHash(event.target.value)}
              className="field-input rounded-lg px-3 py-2 font-mono text-xs"
              placeholder={copy.blockHashPlaceholder}
            />
            <Button onClick={verifyProof} disabled={validationLoading || !blockHash.trim()}>
              {validationLoading ? `${copy.verifyProof}...` : copy.verifyProof}
            </Button>
          </div>
          {validation && (
            <StatusBadge tone={validation.valid ? "success" : "danger"} className="w-fit">
              {validation.message}
            </StatusBadge>
          )}
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <div className="min-h-[92px] rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.merkleProof}</p>
              <p className="break-all font-mono text-[10px] t2">{proof?.merkleProof.join(" / ") || copy.noData}</p>
            </div>
            <div className="min-h-[92px] rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.zkKeys}</p>
              <p className="break-all font-mono text-[10px] t2">{proof?.zkKeys.join(" / ") || copy.noData}</p>
            </div>
          </div>
        </Surface>
      </div>
    </Surface>
  );
}
