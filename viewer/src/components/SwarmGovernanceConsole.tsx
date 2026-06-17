import { useCallback, useEffect, useMemo, useState } from "react";
import { PromptCalibrationDashboard } from "./PromptCalibrationDashboard";
import { Button, MetricTile, ProgressBar, StatusBadge, Surface, toneForStatus } from "./ui/primitives";
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
  cpuPercent?: number;
  memoryMb?: number;
  apiCostUsd?: number;
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
  cloudName?: string;
  latencyMs: number;
  mtls: boolean;
  status: string;
  certSha?: string;
  alert?: string;
};

type BillingStatus = {
  remainingCredits: number;
  spendUsd: number;
  trend: number;
  policy: BillingPolicy;
  billingTier: string;
  billingStatus: string;
};

type BillingPolicy = "strict_limit" | "auto_downscale";

type AuditProof = {
  eventId: string;
  eventHash: string;
  merkleProof: Array<{ hash: string; position: string }>;
  zkKeys: string[];
  root: string;
  zkProof?: Record<string, unknown> | null;
};

type ProofValidation = {
  valid: boolean;
  message: string;
};

type MTLSTunnelStatus = {
  certSha: string;
  issuedAt: string | null;
  expiration: string | null;
  secondsRemaining: number;
  status: "active" | "expiring" | "expired" | "revoked";
};

type GatewayAlert = {
  id: string;
  peerId: string;
  message: string;
  tone: Tone;
};

type RevokedCertificate = {
  certSha: string;
  revokedAt: string | null;
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
  { id: "peer-tpe-01", cloudName: "TPE", latencyMs: 24, mtls: true, status: "connected", certSha: "fallback-cert-tpe" },
  { id: "peer-nrt-02", cloudName: "NRT", latencyMs: 58, mtls: true, status: "connected", certSha: "fallback-cert-nrt" },
  { id: "peer-sjc-03", cloudName: "SJC", latencyMs: 91, mtls: false, status: "signature_error", certSha: "fallback-cert-sjc", alert: "Signature mismatch on tunnel heartbeat." },
];

const fallbackBilling: BillingStatus = {
  remainingCredits: 1842,
  spendUsd: 42.18,
  trend: 12,
  policy: "auto_downscale",
  billingTier: "Premium",
  billingStatus: "active",
};

const fallbackMTLSStatus: MTLSTunnelStatus = {
  certSha: "fallback-cert-sha-256",
  issuedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
  expiration: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
  secondsRemaining: 1800,
  status: "active",
};

const fallbackRevokedCertificates: RevokedCertificate[] = [
  {
    certSha: "revoked-fallback-sha-256-9f1b3c6a8d22",
    revokedAt: new Date(Date.now() - 42 * 60 * 1000).toISOString(),
  },
];

const fallbackMeteredUsage = Array.from({ length: 20 }, (_, index) => Number((0.012 + index * 0.002).toFixed(4)));

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

const API_BASE_URL = "http://localhost:8000";
const ADMIN_API_KEY = "key-admin";

function apiUrl(path: string) {
  return `${API_BASE_URL}${path}`;
}

function wsUrl(path: string) {
  const url = new URL(path, API_BASE_URL);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("api_key", ADMIN_API_KEY);
  return url.toString();
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      "x-api-key": ADMIN_API_KEY,
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
    const cpuPercent = asNumber(record.cpu_percent ?? record.cpuPercent, Number.NaN);
    const memoryMb = asNumber(record.memory_mb ?? record.memoryMb, Number.NaN);
    const apiCostUsd = asNumber(record.usd_cost ?? record.api_cost_usd ?? record.apiCostUsd, Number.NaN);
    return {
      id: asString(record.id ?? record.node_id, `node-${index + 1}`),
      role: asString(record.role ?? record.service_role, "worker"),
      status: asString(record.status, "idle"),
      taskLoad: asNumber(record.task_load ?? record.load ?? record.current_task_load, 0),
      cpuPercent: Number.isFinite(cpuPercent) ? cpuPercent : undefined,
      memoryMb: Number.isFinite(memoryMb) ? memoryMb : undefined,
      apiCostUsd: Number.isFinite(apiCostUsd) ? apiCostUsd : undefined,
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
      id: asString(record.id ?? record.peer_id ?? record.node_id, `peer-${index + 1}`),
      cloudName: asString(record.cloud_name ?? record.cloud ?? record.region, "") || undefined,
      latencyMs: asNumber(record.latency_ms ?? record.latency, 0),
      mtls: asBoolean(record.mtls ?? record.secure ?? record.mtls_enabled, false),
      status: asString(record.status, "connected"),
      certSha: asString(record.cert_sha ?? record.client_cert_sha ?? record.fingerprint, "") || undefined,
      alert: asString(record.alert ?? record.error ?? record.reason, "") || undefined,
    };
  });
}

function mapBilling(raw: unknown): BillingStatus {
  const record = asRecord(raw);
  const data = Object.keys(asRecord(record.data)).length > 0 ? asRecord(record.data) : record;
  const rawPolicy = asString(data.policy, fallbackBilling.policy);
  const policy = rawPolicy === "strict_limit" || rawPolicy === "strict_quota" ? "strict_limit" : "auto_downscale";
  return {
    remainingCredits: asNumber(data.remaining_credits ?? data.remainingCredits, fallbackBilling.remainingCredits),
    spendUsd: asNumber(data.spend_usd ?? data.spendUsd, fallbackBilling.spendUsd),
    trend: asNumber(data.trend ?? data.spend_trend, fallbackBilling.trend),
    policy,
    billingTier: asString(data.billing_tier ?? data.billingTier ?? data.tier, fallbackBilling.billingTier),
    billingStatus: asString(data.billing_status ?? data.billingStatus ?? data.subscription_status ?? data.status, fallbackBilling.billingStatus),
  };
}

function mapTelemetry(raw: unknown) {
  const record = asRecord(raw);
  const telemetry = Object.keys(asRecord(record.telemetry)).length > 0 ? asRecord(record.telemetry) : record;
  const apiCostValue = telemetry.usd_cost ?? telemetry.api_cost_usd ?? telemetry.apiCostUsd;
  const creditsValue = telemetry.credits_remaining ?? telemetry.creditsRemaining ?? telemetry.remaining_credits;
  const activeRoles = readArray(record.active_roles ?? telemetry.active_roles ?? record.activeRoles ?? telemetry.activeRoles, ["roles"])
    .map(role => String(role))
    .filter(Boolean);
  return {
    sessionId: asString(record.session_id ?? telemetry.session_id, "global-session"),
    timestamp: asString(telemetry.timestamp ?? record.timestamp, new Date().toISOString()),
    cpuPercent: asNumber(telemetry.cpu_percent ?? telemetry.cpuPercent, 0),
    memoryMb: asNumber(telemetry.memory_mb ?? telemetry.memoryMb, 0),
    latencyMs: asNumber(telemetry.latency_ms ?? telemetry.latencyMs ?? telemetry.p2p_latency_ms, 0),
    wsLatencyMs: asNumber(telemetry.ws_latency_ms ?? telemetry.wsLatencyMs, 0),
    apiCostUsd: asNumber(apiCostValue, 0),
    hasApiCost: apiCostValue !== undefined,
    creditsRemaining: asNumber(creditsValue, Number.NaN),
    billingTier: asString(telemetry.billing_tier ?? telemetry.billingTier, ""),
    billingStatus: asString(telemetry.billing_status ?? telemetry.billingStatus, ""),
    activeRoles,
  };
}

function deriveTelemetryNodes(current: SwarmNode[], raw: unknown) {
  const telemetry = mapTelemetry(raw);
  const liveNodes = mapNodes(raw);
  if (liveNodes.length > 0) {
    return liveNodes.map(node => ({
      ...node,
      cpuPercent: node.cpuPercent ?? telemetry.cpuPercent,
      memoryMb: node.memoryMb ?? telemetry.memoryMb,
      apiCostUsd: node.apiCostUsd ?? telemetry.apiCostUsd,
    }));
  }
  const roles = telemetry.activeRoles.length > 0
    ? telemetry.activeRoles
    : Array.from(new Set(current.map(node => node.role)));
  const source = current.length > 0
    ? current
    : roles.map((role, index) => ({ id: `${role.toLowerCase()}-${index + 1}`, role, status: "active", taskLoad: 0 }));
  return source.map((node, index) => ({
    ...node,
    role: roles.includes(node.role) ? node.role : node.role,
    status: roles.length === 0 || roles.includes(node.role) ? "active" : node.status,
    taskLoad: Math.max(node.taskLoad, Math.round(telemetry.cpuPercent)),
    cpuPercent: telemetry.cpuPercent,
    memoryMb: telemetry.memoryMb,
    apiCostUsd: telemetry.apiCostUsd,
    id: node.id || `${roles[index] ?? "node"}-${index + 1}`,
  }));
}

function deriveTelemetryPeers(current: PeerNode[], raw: unknown) {
  const telemetry = mapTelemetry(raw);
  const livePeers = mapPeers(raw);
  if (livePeers.length > 0) return livePeers;
  const latency = telemetry.wsLatencyMs || telemetry.latencyMs;
  if (!latency) return current;
  return current.map(peer => ({ ...peer, latencyMs: latency }));
}

function mapAuditProof(raw: unknown, fallbackEventId: string): AuditProof {
  const record = asRecord(raw);
  const data = Object.keys(asRecord(record.data)).length > 0 ? asRecord(record.data) : record;
  const proofSteps = readArray(data.merkle_proof ?? data.merkleProof ?? data.proof, ["proof"]).map(item => {
    const step = asRecord(item);
    return {
      hash: asString(step.hash ?? item, String(item)),
      position: asString(step.position ?? step.direction, "sibling"),
    };
  });
  const zkProof = asRecord(data.zk_proof ?? data.zkProof);
  const zkKeys = [
    asString(data.zk_verification_key ?? data.zkVerificationKey, ""),
    ...Object.entries(zkProof).map(([key, value]) => `${key}:${String(value)}`),
  ].filter(Boolean);
  return {
    eventId: String(data.event_id ?? data.eventId ?? fallbackEventId),
    eventHash: asString(data.event_hash ?? data.eventHash, ""),
    merkleProof: proofSteps,
    zkKeys,
    root: asString(data.root_hash ?? data.rootHash ?? data.root ?? data.merkle_root, "0x00000000000000000000"),
    zkProof: Object.keys(zkProof).length > 0 ? zkProof : null,
  };
}

function normalizeMTLSStatus(value: string, secondsRemaining: number): MTLSTunnelStatus["status"] {
  const status = value.toLowerCase();
  if (status.includes("revoked")) return "revoked";
  if (status.includes("expired") || secondsRemaining <= 0) return "expired";
  if (status.includes("expiring") || secondsRemaining <= 360) return "expiring";
  return "active";
}

function mapMTLSStatus(raw: unknown): MTLSTunnelStatus {
  const record = asRecord(raw);
  const data = Object.keys(asRecord(record.data)).length > 0 ? asRecord(record.data) : record;
  const expiration = asString(data.expiration ?? data.expires_at ?? data.expiry, fallbackMTLSStatus.expiration ?? "");
  const secondsRemaining = asNumber(data.seconds_remaining ?? data.secondsRemaining, fallbackMTLSStatus.secondsRemaining);
  const status = normalizeMTLSStatus(asString(data.cert_status ?? data.status, fallbackMTLSStatus.status), secondsRemaining);
  return {
    certSha: asString(data.cert_sha ?? data.sha256 ?? data.fingerprint, fallbackMTLSStatus.certSha),
    issuedAt: asString(data.issued_at ?? data.issuedAt ?? data.created_at ?? data.createdAt, fallbackMTLSStatus.issuedAt ?? "") || null,
    expiration: expiration || null,
    secondsRemaining,
    status,
  };
}

function mapRevokedCertificates(raw: unknown): RevokedCertificate[] {
  const items = readArray(raw, ["revoked_certificates", "revokedCertificates", "certificates", "data"]);
  return items.map(item => {
    const record = asRecord(item);
    return {
      certSha: asString(record.cert_sha ?? record.client_cert_sha ?? record.sha ?? item, String(item)),
      revokedAt: asString(record.revoked_at ?? record.revokedAt ?? record.timestamp, "") || null,
    };
  }).filter(item => item.certSha.length > 0);
}

function secondsUntil(status: MTLSTunnelStatus, nowMs: number) {
  if (status.expiration) {
    const expiryMs = Date.parse(status.expiration);
    if (Number.isFinite(expiryMs)) return Math.max(0, Math.floor((expiryMs - nowMs) / 1000));
  }
  return Math.max(0, Math.floor(status.secondsRemaining));
}

function formatCountdown(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

function mtlsTone(status: MTLSTunnelStatus["status"]) {
  if (status === "active") return "success";
  if (status === "expiring") return "warning";
  return "danger";
}

function truncateFingerprint(value: string) {
  return value.length > 18 ? `${value.slice(0, 12)}...${value.slice(-6)}` : value;
}

function formatRevokedAt(value: string | null) {
  if (!value) return "not reported";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

function deriveGatewayAlerts(peers: PeerNode[]) {
  return peers.flatMap<GatewayAlert>(peer => {
    const status = peer.status.toLowerCase();
    const message = peer.alert
      || (status.includes("signature") ? "Tunnel signature validation failed." : "")
      || (status.includes("heartbeat") || status.includes("timeout") ? "Tunnel heartbeat failed." : "")
      || (status.includes("offline") || status.includes("failed") || status.includes("error") ? "Peer tunnel is reporting a connection failure." : "");
    return message
      ? [{
        id: `${peer.id}-${status}`,
        peerId: peer.id,
        message,
        tone: status.includes("signature") || status.includes("revoked") ? "danger" : "warning",
      }]
      : [];
  });
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

function nodeStatusTone(status: string) {
  const value = status.toLowerCase();
  if (value === "idle") return "success";
  if (value === "busy") return "accent";
  return toneForStatus(status);
}

export function SwarmNodeMonitor({
  copy,
  drawerOpen,
  groupedNodes,
  healthLogs,
  onToggle,
  onScale,
}: {
  copy: GovernanceCopy;
  drawerOpen: boolean;
  groupedNodes: Record<string, SwarmNode[]>;
  healthLogs: HealthLog[];
  onToggle: () => void;
  onScale: (role: string, direction: "up" | "down") => void;
}) {
  return (
    <Surface className="flex flex-col gap-3 p-3 xl:col-span-4" data-testid="swarm-node-monitor">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.nodeRegistry}</h3>
        <Button onClick={onToggle} className="px-2 py-1 text-[10px]">
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
                  <Button onClick={() => onScale(role, "down")} title={copy.scaleDown} className="h-7 w-7 px-0 py-0">-</Button>
                  <Button onClick={() => onScale(role, "up")} title={copy.scaleUp} variant="primary" className="h-7 w-7 px-0 py-0">+</Button>
                </div>
              </div>
              <div className="flex flex-col gap-2">
                {roleNodes.map(node => (
                  <div key={node.id} className="grid grid-cols-[1fr_auto] gap-2 text-[10px]">
                    <div className="min-w-0">
                      <p className="truncate font-mono font-semibold t2">{node.id}</p>
                      <ProgressBar value={node.taskLoad} tone={node.taskLoad > 72 ? "warning" : "accent"} className="mt-1" />
                      <p className="mt-1 truncate font-mono text-[9px] t3">
                        CPU {node.cpuPercent?.toFixed(1) ?? "--"}% / MEM {node.memoryMb?.toFixed(1) ?? "--"}MB / ${node.apiCostUsd?.toFixed(4) ?? "0.0000"}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <StatusBadge tone={nodeStatusTone(node.status)}>{node.status}</StatusBadge>
                      <span className="font-mono t3">{copy.load} {node.taskLoad}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="rounded-lg border p-3 font-mono text-[10px]" style={{ borderColor: "var(--border-c)", background: "color-mix(in srgb, var(--warning-bg) 42%, var(--bg-card))" }}>
        <p className="mb-2 text-[10px] font-black uppercase tracking-[0.14em]" style={{ color: "var(--warning)" }}>{copy.heartbeatLog}</p>
        {healthLogs.map(log => (
          <div key={log.id} className="mb-2 grid grid-cols-[58px_1fr] gap-2 last:mb-0">
            <span className="t3">{log.timestamp}</span>
            <span style={{ color: log.tone === "warning" ? "var(--warning)" : "var(--t2)" }}>
              [{log.nodeId}] {log.message}
            </span>
          </div>
        ))}
      </div>
    </Surface>
  );
}

export function SessionFailoverDashboard({
  copy,
  sessions,
  resumeLoading,
  onResume,
}: {
  copy: GovernanceCopy;
  sessions: SwarmSession[];
  resumeLoading: string | null;
  onResume: (sessionId: string) => void;
}) {
  return (
    <Surface className="flex flex-col gap-3 p-3 xl:col-span-4" data-testid="session-failover-dashboard">
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
            <ProgressBar value={(session.completed / Math.max(1, session.total)) * 100} className="mt-3" tone={session.completed === session.total ? "success" : "accent"} />
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
              onClick={() => onResume(session.id)}
              disabled={resumeLoading === session.id}
              variant="primary"
              className="mt-3 w-full"
            >
              {resumeLoading === session.id ? <span className="typing-dots">{copy.resuming}</span> : copy.forceResume}
            </Button>
          </div>
        ))}
      </div>
    </Surface>
  );
}

export function P2PMeshNetworkMap({
  copy,
  peers,
  revokingPeerId,
  onRevokePeer,
}: {
  copy: GovernanceCopy;
  peers: PeerNode[];
  revokingPeerId: string | null;
  onRevokePeer: (peer: PeerNode) => void;
}) {
  return (
    <Surface className="flex flex-col gap-3 p-3 xl:col-span-4" data-testid="p2p-mesh-network-map">
      <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.peers}</h3>
      <div className="overflow-hidden rounded-lg border" style={{ borderColor: "var(--border-c)" }}>
        {peers.map(peer => (
          <div key={peer.id} className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-2 border-b px-3 py-2 text-[10px] last:border-b-0" style={{ borderColor: "var(--border-c)" }}>
            <div className="min-w-0">
              <p className="truncate font-mono font-semibold t2">{peer.id}</p>
              <p className="truncate t3">{peer.status}{peer.certSha ? ` / ${peer.certSha.slice(0, 10)}...` : ""}</p>
            </div>
            <span className="flex items-center gap-1.5 font-mono t2">
              <span className="h-2 w-2 rounded-full" style={{ background: peer.latencyMs < 50 ? "var(--success)" : "var(--warning)" }} />
              {peer.latencyMs}ms
            </span>
            <StatusBadge tone={peer.mtls ? "success" : "warning"}>{peer.mtls ? copy.locked : copy.unlocked}</StatusBadge>
            <Button
              onClick={() => onRevokePeer(peer)}
              disabled={revokingPeerId === peer.id}
              variant="danger"
              className="px-2 py-1 text-[10px]"
            >
              {revokingPeerId === peer.id ? "Revoking" : "Revoke"}
            </Button>
          </div>
        ))}
      </div>
    </Surface>
  );
}

export function MTLSTunnelingStatusPanel({
  certStatus,
  countdownSeconds,
  alerts,
  revokedCertificates,
  reinstatingCertSha,
  reinstatedCertSha,
  rotationLoading,
  onRotate,
  onCopyCertificate,
  onReinstateCertificate,
}: {
  certStatus: MTLSTunnelStatus;
  countdownSeconds: number;
  alerts: GatewayAlert[];
  revokedCertificates: RevokedCertificate[];
  reinstatingCertSha: string | null;
  reinstatedCertSha: string | null;
  rotationLoading: boolean;
  onRotate: () => void;
  onCopyCertificate: (sha: string) => void;
  onReinstateCertificate: (sha: string) => void;
}) {
  const status = normalizeMTLSStatus(certStatus.status, countdownSeconds);
  return (
    <Surface
      className="flex flex-col gap-3 p-3"
      data-testid="mtls-tunneling-status-panel"
      style={{
        background: "linear-gradient(145deg, hsl(218 18% 12% / 0.9), hsl(223 26% 8% / 0.96))",
        borderColor: "hsl(210 22% 24% / 0.88)",
        boxShadow: "inset 0 1px 0 hsl(0 0% 100% / 0.05), 0 20px 55px hsl(220 46% 3% / 0.34)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">mTLS Tunneling Status</h3>
          <p className="mt-1 text-[10px] t3">Client certificate lifecycle, cross-cloud tunnel trust, and gateway alerts.</p>
        </div>
        <StatusBadge tone={mtlsTone(status)}>{status}</StatusBadge>
      </div>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
        <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] t3">SHA-256 fingerprint</p>
          <p className="mt-1 break-all font-mono text-[10px] t2">{certStatus.certSha}</p>
        </div>
        <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] t3">Issued</p>
          <p className="mt-1 font-mono text-[10px] t2">{certStatus.issuedAt ?? "not reported"}</p>
          <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">Expires</p>
          <p className="mt-1 font-mono text-[10px] t2">{certStatus.expiration ?? "not reported"}</p>
        </div>
        <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] t3">Countdown</p>
          <p className="mt-1 font-mono text-xl font-semibold t1">{formatCountdown(countdownSeconds)}</p>
          <Button onClick={onRotate} disabled={rotationLoading} variant="primary" className="mt-3 w-full">
            {rotationLoading ? "Rotating Keys" : "Force Rotate Keys"}
          </Button>
        </div>
      </div>
      <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: alerts.length > 0 ? "var(--warning-bg)" : "var(--bg-muted)" }}>
        <p className="mb-2 text-[10px] font-black uppercase tracking-[0.14em] t2">Connection Alerts</p>
        {alerts.length > 0 ? alerts.map(alert => (
          <div key={alert.id} className="mb-2 grid grid-cols-[auto_1fr] gap-2 text-[10px] last:mb-0">
            <StatusBadge tone={alert.tone}>{alert.peerId}</StatusBadge>
            <span className="t2">{alert.message}</span>
          </div>
        )) : <p className="text-[10px] t3">No tunnel heartbeat or signature warnings.</p>}
      </div>
      <div className="rounded-lg border p-3" style={{ borderColor: "hsl(214 24% 24% / 0.9)", background: "hsl(218 20% 10% / 0.72)" }}>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.14em] t2">Revoked Certificates Ledger</p>
            <p className="mt-1 text-[10px] t3">Certificate reinstatement queue for cross-cloud mTLS trust.</p>
          </div>
          <StatusBadge tone={revokedCertificates.length > 0 ? "warning" : "success"}>{revokedCertificates.length} revoked</StatusBadge>
        </div>
        <div className="overflow-hidden rounded-lg border" style={{ borderColor: "hsl(214 24% 24% / 0.9)" }}>
          {revokedCertificates.length > 0 ? revokedCertificates.map(certificate => {
            const loading = reinstatingCertSha === certificate.certSha;
            const success = reinstatedCertSha === certificate.certSha;
            return (
              <div
                key={certificate.certSha}
                className="grid grid-cols-1 gap-2 border-b px-3 py-2 text-[10px] transition-all duration-200 last:border-b-0 hover:grayscale hover:brightness-110 md:grid-cols-[1fr_1fr_auto]"
                style={{ borderColor: "hsl(214 24% 24% / 0.9)", background: "hsl(220 18% 9% / 0.58)" }}
              >
                <div className="min-w-0">
                  <p className="mb-1 text-[9px] font-bold uppercase tracking-[0.12em] t3">SHA-256 fingerprint</p>
                  <div className="flex items-center gap-2">
                    <span className="truncate font-mono t2">{truncateFingerprint(certificate.certSha)}</span>
                    <Button onClick={() => onCopyCertificate(certificate.certSha)} className="px-2 py-1 text-[10px]">Copy</Button>
                  </div>
                </div>
                <div className="min-w-0">
                  <p className="mb-1 text-[9px] font-bold uppercase tracking-[0.12em] t3">Revoked at</p>
                  <p className="truncate font-mono t2">{formatRevokedAt(certificate.revokedAt)}</p>
                </div>
                <Button
                  onClick={() => onReinstateCertificate(certificate.certSha)}
                  disabled={loading}
                  variant={success ? "primary" : "warning"}
                  className="justify-self-start px-3 py-1 text-[10px] transition-all duration-300 md:justify-self-end"
                  style={{
                    borderColor: success ? "hsl(194 90% 58%)" : "hsl(38 78% 55% / 0.78)",
                    boxShadow: success ? "0 0 18px hsl(194 95% 56% / 0.52)" : "none",
                  }}
                >
                  {loading && <span className="mr-1 inline-block h-3 w-3 animate-spin rounded-full border border-current border-t-transparent align-[-2px]" />}
                  {success ? "Reinstated" : "Reinstate"}
                </Button>
              </div>
            );
          }) : (
            <div className="px-3 py-4 text-[10px] t3">No revoked certificates in the current ledger.</div>
          )}
        </div>
      </div>
    </Surface>
  );
}

function CreditProgressRing({
  credits,
  maxCredits = 2000,
}: {
  credits: number;
  maxCredits?: number;
}) {
  const percent = Math.max(0, Math.min(100, (credits / Math.max(1, maxCredits)) * 100));
  const radius = 35;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const gradientEnd = percent > 35 ? "hsl(154 55% 48%)" : "hsl(38 80% 56%)";
  return (
    <div className="relative grid place-items-center">
      <svg viewBox="0 0 92 92" className="h-24 w-24 -rotate-90">
        <defs>
          <linearGradient id="credits-ring-gradient" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="hsl(166 58% 45%)" />
            <stop offset="100%" stopColor={gradientEnd} />
          </linearGradient>
        </defs>
        <circle cx="46" cy="46" r={radius} fill="none" stroke="hsl(210 16% 22% / 0.8)" strokeWidth="8" />
        <circle
          cx="46"
          cy="46"
          r={radius}
          fill="none"
          stroke="url(#credits-ring-gradient)"
          strokeLinecap="round"
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute text-center">
        <p className="font-mono text-lg font-semibold t1">{Math.round(credits).toLocaleString()}</p>
        <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">credits</p>
      </div>
    </div>
  );
}

function MeteredUsageSparkline({ points }: { points: number[] }) {
  const max = Math.max(...points, 0.001);
  return (
    <div className="flex h-20 items-end gap-1 overflow-hidden rounded-lg border px-2 py-2" style={{ borderColor: "hsl(214 24% 24% / 0.9)", background: "linear-gradient(180deg, hsl(216 18% 12% / 0.82), hsl(220 22% 8% / 0.72))" }}>
      {points.map((point, index) => {
        const height = Math.max(8, (point / max) * 64);
        return (
          <span
            key={`${index}-${point}`}
            className="w-full rounded-t-sm transition-all duration-300 ease-out"
            style={{
              height,
              background: "linear-gradient(180deg, hsl(190 72% 55%), hsl(156 50% 42%))",
              opacity: 0.36 + (index / Math.max(1, points.length - 1)) * 0.58,
              transform: `translateX(${Math.max(0, points.length - 20) * -2}px)`,
            }}
            title={`$${point.toFixed(4)}`}
          />
        );
      })}
    </div>
  );
}

export function BillingPolicyControls({
  copy,
  billing,
  meteredUsage,
  policyLoading,
  onPolicyChange,
}: {
  copy: GovernanceCopy;
  billing: BillingStatus;
  meteredUsage: number[];
  policyLoading: boolean;
  onPolicyChange: (policy: BillingPolicy) => void;
}) {
  const tier = billing.billingTier || "Standard";
  const status = billing.billingStatus || "active";
  return (
    <Surface
      className="flex flex-col gap-3 p-3"
      data-testid="billing-policy-controls"
      style={{
        background: "linear-gradient(135deg, hsl(217 18% 12% / 0.88), hsl(220 24% 8% / 0.94))",
        borderColor: "hsl(210 24% 24% / 0.9)",
        boxShadow: "inset 0 1px 0 hsl(0 0% 100% / 0.045), 0 18px 50px hsl(220 45% 3% / 0.32)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.billing}</h3>
        <StatusBadge tone={status.toLowerCase() === "active" ? "success" : "warning"}>{tier} / {status}</StatusBadge>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-[auto_1fr]">
        <CreditProgressRing credits={billing.remainingCredits} />
        <div className="grid grid-cols-2 gap-3">
          <MetricTile label={copy.remainingCredits} value={billing.remainingCredits.toLocaleString()} tone="success" />
          <MetricTile label={`${copy.spendTrend} +${billing.trend}%`} value={`$${billing.spendUsd.toFixed(2)}`} tone="accent" />
          <div className="col-span-2 rounded-lg border p-3" style={{ borderColor: "hsl(214 24% 24% / 0.9)", background: "hsl(218 20% 10% / 0.68)" }}>
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] t3">Metered Token Usage (Real-time)</p>
              <span className="font-mono text-[10px] t3">{meteredUsage.length}/20</span>
            </div>
            <MeteredUsageSparkline points={meteredUsage} />
          </div>
        </div>
      </div>
      <label className="text-[10px] font-bold uppercase tracking-[0.12em] t3" htmlFor="billing-policy-select">
        {copy.policy}
      </label>
      <select
        id="billing-policy-select"
        value={billing.policy}
        onChange={event => onPolicyChange(event.target.value as BillingPolicy)}
        disabled={policyLoading}
        className="field-input rounded-lg px-3 py-2 text-xs"
      >
        <option value="strict_limit">{copy.strictQuota}</option>
        <option value="auto_downscale">{copy.autoDownscale}</option>
      </select>
    </Surface>
  );
}

export function CryptographicProofInspector({
  copy,
  proofEventId,
  proof,
  proofLoading,
  blockHash,
  validation,
  validationLoading,
  modalOpen,
  onEventIdChange,
  onBlockHashChange,
  onLoadProof,
  onVerifyProof,
  onCloseModal,
}: {
  copy: GovernanceCopy;
  proofEventId: string;
  proof: AuditProof | null;
  proofLoading: boolean;
  blockHash: string;
  validation: ProofValidation | null;
  validationLoading: boolean;
  modalOpen: boolean;
  onEventIdChange: (eventId: string) => void;
  onBlockHashChange: (hash: string) => void;
  onLoadProof: () => void;
  onVerifyProof: () => void;
  onCloseModal: () => void;
}) {
  return (
    <Surface className="flex flex-col gap-3 p-3" data-testid="cryptographic-proof-inspector">
      <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.proofInspector}</h3>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
        <label className="sr-only" htmlFor="audit-proof-event">{copy.eventId}</label>
        <input
          id="audit-proof-event"
          value={proofEventId}
          onChange={event => onEventIdChange(event.target.value)}
          className="field-input rounded-lg px-3 py-2 font-mono text-xs"
          placeholder={copy.eventId}
        />
        <Button onClick={onLoadProof} disabled={proofLoading} variant="primary">
          {proofLoading ? `${copy.loadProof}...` : copy.loadProof}
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
        <label className="sr-only" htmlFor="audit-proof-hash">{copy.verifyProof}</label>
        <input
          id="audit-proof-hash"
          value={blockHash}
          onChange={event => onBlockHashChange(event.target.value)}
          className="field-input rounded-lg px-3 py-2 font-mono text-xs"
          placeholder={copy.blockHashPlaceholder}
        />
        <Button onClick={onVerifyProof} disabled={validationLoading || !blockHash.trim()}>
          {validationLoading ? `${copy.verifyProof}...` : copy.verifyProof}
        </Button>
      </div>
      {validation && (
        <StatusBadge tone={validation.valid ? "success" : "danger"} className="w-fit">
          {validation.valid ? "Verified" : "Tampered"}: {validation.message}
        </StatusBadge>
      )}
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <div className="min-h-[92px] rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.merkleProof}</p>
          <p className="break-all font-mono text-[10px] t2">
            {proof?.merkleProof.map(step => `${step.position}:${step.hash}`).join(" / ") || copy.noData}
          </p>
        </div>
        <div className="min-h-[92px] rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.zkKeys}</p>
          <p className="break-all font-mono text-[10px] t2">{proof?.zkKeys.join(" / ") || copy.noData}</p>
        </div>
      </div>
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-4">
          <Surface className="flex w-full max-w-2xl flex-col gap-3 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-xs font-black uppercase tracking-[0.14em] t1">{copy.proofInspector}</h3>
                <p className="mt-1 font-mono text-[10px] t3">{proof?.eventId || proofEventId}</p>
              </div>
              <Button onClick={onCloseModal} className="px-2 py-1 text-[10px]">{copy.collapse}</Button>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.merkleProof}</p>
                <div className="flex flex-col gap-1">
                  {proof?.merkleProof.length
                    ? proof.merkleProof.map((step, index) => (
                      <div key={`${step.hash}-${index}`} className="rounded border px-2 py-1 font-mono text-[10px] t2" style={{ borderColor: "var(--border-c)" }}>
                        <span className="font-semibold">{index + 1}. {step.position}</span> {step.hash}
                      </div>
                    ))
                    : <p className="font-mono text-[10px] t2">{copy.noData}</p>}
                </div>
              </div>
              <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
                <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.zkKeys}</p>
                <p className="break-all font-mono text-[10px] t2">{proof?.zkKeys.join("\n") || copy.noData}</p>
              </div>
            </div>
          </Surface>
        </div>
      )}
    </Surface>
  );
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
  const [mtlsStatus, setMTLSStatus] = useState<MTLSTunnelStatus>(fallbackMTLSStatus);
  const [revokedCertificates, setRevokedCertificates] = useState<RevokedCertificate[]>(fallbackRevokedCertificates);
  const [reinstatingCertSha, setReinstatingCertSha] = useState<string | null>(null);
  const [reinstatedCertSha, setReinstatedCertSha] = useState<string | null>(null);
  const [meteredUsage, setMeteredUsage] = useState<number[]>(fallbackMeteredUsage);
  const [nowMs, setNowMs] = useState(Date.now());
  const [rotationLoading, setRotationLoading] = useState(false);
  const [revokingPeerId, setRevokingPeerId] = useState<string | null>(null);
  const [socketAlerts, setSocketAlerts] = useState<GatewayAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [resumeLoading, setResumeLoading] = useState<string | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [proofEventId, setProofEventId] = useState("event-001");
  const [proof, setProof] = useState<AuditProof | null>(null);
  const [proofLoading, setProofLoading] = useState(false);
  const [blockHash, setBlockHash] = useState("");
  const [validation, setValidation] = useState<ProofValidation | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [proofModalOpen, setProofModalOpen] = useState(false);

  const groupedNodes = useMemo(() => groupNodesByRole(nodes), [nodes]);
  const countdownSeconds = useMemo(() => secondsUntil(mtlsStatus, nowMs), [mtlsStatus, nowMs]);
  const gatewayAlerts = useMemo(() => [
    ...deriveGatewayAlerts(peers),
    ...socketAlerts,
  ].slice(0, 5), [peers, socketAlerts]);

  const applyTelemetryPayload = useCallback((raw: unknown) => {
    const telemetry = mapTelemetry(raw);
    setNodes(current => deriveTelemetryNodes(current, raw));
    setPeers(current => deriveTelemetryPeers(current, raw));
    setBilling(current => ({
      ...current,
      spendUsd: Math.max(current.spendUsd, telemetry.apiCostUsd),
      trend: telemetry.apiCostUsd > current.spendUsd ? Math.round(((telemetry.apiCostUsd - current.spendUsd) / Math.max(1, current.spendUsd)) * 100) : current.trend,
      remainingCredits: Number.isFinite(telemetry.creditsRemaining) ? telemetry.creditsRemaining : current.remainingCredits,
      billingTier: telemetry.billingTier || current.billingTier,
      billingStatus: telemetry.billingStatus || current.billingStatus,
    }));
    if (telemetry.hasApiCost) {
      setMeteredUsage(current => [...current.slice(-19), telemetry.apiCostUsd]);
    }
    const timestamp = telemetry.timestamp.split("T").pop()?.slice(0, 8) ?? "--:--:--";
    setHealthLogs(current => [
      {
        id: `telemetry-${telemetry.timestamp}`,
        timestamp,
        nodeId: telemetry.sessionId,
        message: `Telemetry stream CPU ${telemetry.cpuPercent.toFixed(1)}%, memory ${telemetry.memoryMb.toFixed(1)}MB, latency ${(telemetry.wsLatencyMs || telemetry.latencyMs).toFixed(1)}ms.`,
        tone: (telemetry.cpuPercent > 85 || (telemetry.wsLatencyMs || telemetry.latencyMs) > 250 ? "warning" : "success") as Tone,
      },
      ...current.filter(log => !log.id.startsWith("telemetry-")),
    ].slice(0, 5));
  }, []);

  const loadGovernanceData = useCallback(async () => {
    setLoading(true);
    const [nodeResult, healthResult, sessionResult, peerResult, billingResult, mtlsResult, revokedResult] = await Promise.allSettled([
      fetchJson<unknown>(apiUrl("/v1/swarm/nodes")),
      fetchJson<unknown>(apiUrl("/v1/swarm/health")),
      fetchJson<unknown>(apiUrl("/v1/swarm/sessions")),
      fetchJson<unknown>(apiUrl("/v1/swarm/peers")),
      fetchJson<unknown>(apiUrl("/v1/swarm/billing/status")),
      fetchJson<unknown>(apiUrl("/v1/cross-cloud/cert/status")),
      fetchJson<unknown>(apiUrl("/v1/cross-cloud/revoked")),
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
    if (mtlsResult.status === "fulfilled") {
      setMTLSStatus(mapMTLSStatus(mtlsResult.value));
    } else {
      usedFallback = true;
      setMTLSStatus(fallbackMTLSStatus);
    }
    if (revokedResult.status === "fulfilled") {
      const nextRevoked = mapRevokedCertificates(revokedResult.value);
      setRevokedCertificates(nextRevoked.length > 0 ? nextRevoked : []);
    } else {
      usedFallback = true;
      setRevokedCertificates(fallbackRevokedCertificates);
    }
    setLoading(false);
    onStatus(usedFallback ? copy.offline : copy.loaded, usedFallback ? "warning" : "success");
  }, [copy.loaded, copy.offline, onStatus]);

  useEffect(() => {
    void loadGovernanceData();
  }, [loadGovernanceData]);

  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let closed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;

    function connect() {
      socket = new WebSocket(wsUrl("/v1/swarm/telemetry/ws"));
      socket.onmessage = event => {
        try {
          applyTelemetryPayload(JSON.parse(event.data) as unknown);
        } catch (error) {
          onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "warning");
        }
      };
      socket.onclose = () => {
        if (!closed) {
          setSocketAlerts(current => [{
            id: `telemetry-socket-${Date.now()}`,
            peerId: "telemetry-ws",
            message: "Telemetry tunnel heartbeat closed; reconnect scheduled.",
            tone: "warning" as Tone,
          }, ...current].slice(0, 3));
          reconnectTimer = window.setTimeout(connect, 5000);
        }
      };
      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();
    return () => {
      closed = true;
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [applyTelemetryPayload, copy.actionFailed, onStatus]);

  async function scaleRole(role: string, direction: "up" | "down") {
    try {
      await fetchJson<unknown>(apiUrl("/v1/swarm/scale"), {
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
      await fetchJson<unknown>(apiUrl("/v1/swarm/sessions/resume"), {
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
      await fetchJson<unknown>(apiUrl("/v1/swarm/billing/policy"), {
        method: "POST",
        body: JSON.stringify({ policy }),
      });
      onStatus(`${copy.policy}: ${policy === "strict_limit" ? copy.strictQuota : copy.autoDownscale}`);
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    } finally {
      setPolicyLoading(false);
    }
  }

  async function rotateKeys() {
    setRotationLoading(true);
    try {
      const raw = await fetchJson<unknown>(apiUrl("/v1/cross-cloud/cert/rotate"), { method: "POST" });
      setMTLSStatus(mapMTLSStatus(raw));
      setNowMs(Date.now());
      setSocketAlerts(current => current.filter(alert => alert.peerId !== "cert-rotation"));
      onStatus("mTLS client certificate rotated.", "success");
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    } finally {
      setRotationLoading(false);
    }
  }

  async function revokePeer(peer: PeerNode) {
    setRevokingPeerId(peer.id);
    try {
      await fetchJson<unknown>(apiUrl("/v1/cross-cloud/revoke"), {
        method: "POST",
        body: JSON.stringify({
          cloud_name: peer.cloudName ?? peer.id,
          client_cert_sha: peer.certSha,
        }),
      });
      setPeers(current => current.filter(item => item.id !== peer.id));
      if (peer.certSha) {
        setRevokedCertificates(current => [
          { certSha: peer.certSha ?? peer.id, revokedAt: new Date().toISOString() },
          ...current.filter(item => item.certSha !== peer.certSha),
        ]);
      }
      setSocketAlerts(current => [{
        id: `revoked-${peer.id}-${Date.now()}`,
        peerId: peer.id,
        message: "Peer cloud gateway revoked and removed from the local mesh view.",
        tone: "warning" as Tone,
      }, ...current].slice(0, 3));
      onStatus(`${peer.id}: cross-cloud gateway revoked.`, "success");
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    } finally {
      setRevokingPeerId(null);
    }
  }

  async function copyCertificate(sha: string) {
    try {
      await navigator.clipboard.writeText(sha);
      onStatus("Certificate fingerprint copied.", "success");
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "warning");
    }
  }

  async function reinstateCertificate(sha: string) {
    setReinstatingCertSha(sha);
    setReinstatedCertSha(null);
    try {
      await fetchJson<unknown>(apiUrl("/v1/cross-cloud/reinstate"), {
        method: "POST",
        body: JSON.stringify({ client_cert_sha: sha }),
      });
      setRevokedCertificates(current => current.filter(item => item.certSha !== sha));
      setReinstatedCertSha(sha);
      window.setTimeout(() => setReinstatedCertSha(current => current === sha ? null : current), 2200);
      onStatus("Certificate reinstated.", "success");
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    } finally {
      setReinstatingCertSha(null);
    }
  }

  async function loadProof() {
    if (!proofEventId.trim()) return;
    setProofLoading(true);
    setProof(null);
    try {
      const raw = await fetchJson<unknown>(apiUrl(`/v1/audit/proof/${encodeURIComponent(proofEventId.trim())}`));
      const nextProof = mapAuditProof(raw, proofEventId);
      setProof(nextProof);
      setBlockHash(nextProof.eventHash);
      setProofModalOpen(true);
    } catch (error) {
      setProof({
        eventId: proofEventId,
        eventHash: blockHash.trim(),
        merkleProof: [
          { position: "left", hash: "fallback-sibling-left" },
          { position: "right", hash: "fallback-sibling-right" },
        ],
        zkKeys: ["local-verifier-key", "session-public-input"],
        root: "fallback-root",
        zkProof: null,
      });
      setProofModalOpen(true);
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "warning");
    } finally {
      setProofLoading(false);
    }
  }

  async function verifyProof() {
    if (!proof && !blockHash.trim()) return;
    setValidationLoading(true);
    setValidation(null);
    try {
      const eventHash = blockHash.trim() || proof?.eventHash || "";
      const raw = await fetchJson<unknown>(apiUrl("/v1/audit/verify-proof"), {
        method: "POST",
        body: JSON.stringify({
          event_hash: eventHash,
          proof: proof?.merkleProof ?? [],
          root_hash: proof?.root ?? "",
        }),
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
        <SwarmNodeMonitor
          copy={copy}
          drawerOpen={drawerOpen}
          groupedNodes={groupedNodes}
          healthLogs={healthLogs}
          onToggle={() => setDrawerOpen(value => !value)}
          onScale={scaleRole}
        />
        <SessionFailoverDashboard
          copy={copy}
          sessions={sessions}
          resumeLoading={resumeLoading}
          onResume={resumeSession}
        />
        <P2PMeshNetworkMap
          copy={copy}
          peers={peers}
          revokingPeerId={revokingPeerId}
          onRevokePeer={revokePeer}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MTLSTunnelingStatusPanel
          certStatus={mtlsStatus}
          countdownSeconds={countdownSeconds}
          alerts={gatewayAlerts}
          revokedCertificates={revokedCertificates}
          reinstatingCertSha={reinstatingCertSha}
          reinstatedCertSha={reinstatedCertSha}
          rotationLoading={rotationLoading}
          onRotate={rotateKeys}
          onCopyCertificate={copyCertificate}
          onReinstateCertificate={reinstateCertificate}
        />
        <BillingPolicyControls
          copy={copy}
          billing={billing}
          meteredUsage={meteredUsage}
          policyLoading={policyLoading}
          onPolicyChange={updatePolicy}
        />
        <CryptographicProofInspector
          copy={copy}
          proofEventId={proofEventId}
          proof={proof}
          proofLoading={proofLoading}
          blockHash={blockHash}
          validation={validation}
          validationLoading={validationLoading}
          modalOpen={proofModalOpen}
          onEventIdChange={setProofEventId}
          onBlockHashChange={setBlockHash}
          onLoadProof={loadProof}
          onVerifyProof={verifyProof}
          onCloseModal={() => setProofModalOpen(false)}
        />
      </div>

      <PromptCalibrationDashboard lang={lang} onStatus={onStatus} />
    </Surface>
  );
}
