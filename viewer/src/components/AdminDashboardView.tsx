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
import {
  ReplayPlaybackWidget,
  SwarmGovernanceConsole,
  type SwarmReplayEvent,
} from "./SwarmGovernanceConsole";
import { logUiDiagnostic } from "../utils/logger";
import type { Lang, TranslationMessages } from "../types";

type AdminDashboardViewProps = {
  t: TranslationMessages;
  lang: Lang;
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

type AdminCopy = {
  intro: string;
  refresh: string;
  loadingTenants: string;
  errorPrefix: string;
  none: string;
  rotateTitle: string;
  rotate: string;
  keyRotated: string;
  active: string;
  freeze: string;
  cancel: string;
  wsLive: string;
  offlineSimulation: string;
  lastNode: string;
  latency: string;
  markupApplied: string;
  hitlTitle: string;
  close: string;
  hitlPlaceholder: string;
  submitHijack: string;
  ledgerSubtitle: string;
  healthy: string;
  tampered: string;
  merkleRoot: string;
  blockValidationCount: string;
  blocksVerified: string;
  auditBreach: string;
  verifying: string;
  verifyChain: string;
  simulateTamper: string;
  keyRotationFailed: string;
  statusUpdateFailed: string;
  pauseFailed: string;
  resumeFailed: string;
  hijackSuccess: string;
  hijackFailed: string;
  ledgerLoadFailed: string;
  swarmInitialized: string;
  debateMessage: (currentAgent: string, targetAgent: string) => string;
  blockLabel: string;
  hashLabel: string;
  sessionLabel: string;
  stripeLabel: string;
  totalTokens: string;
  cost: string;
  tpmLimit: string;
};

const ADMIN_COPY: Record<Lang, AdminCopy> = {
  zh: {
    intro: "租戶隔離、計費限制、WebSocket 攔截與 SOC2 審計狀態集中管理。",
    refresh: "重新整理",
    loadingTenants: "正在載入租戶...",
    errorPrefix: "錯誤",
    none: "無",
    rotateTitle: "輪替租戶 API key",
    rotate: "輪替",
    keyRotated: "Key 已在記憶體中輪替。",
    active: "啟用",
    freeze: "凍結",
    cancel: "取消",
    wsLive: "WebSocket 連線中",
    offlineSimulation: "離線模擬",
    lastNode: "最後節點",
    latency: "延遲",
    markupApplied: "已套用加成費率",
    hitlTitle: "注入人工介入輸入",
    close: "關閉",
    hitlPlaceholder: "輸入回應 mock 值或直接指令，用於覆寫原生工具執行...",
    submitHijack: "送出人工介入輸入",
    ledgerSubtitle: "SOC2 SHA-256 審計鏈",
    healthy: "健康",
    tampered: "遭竄改",
    merkleRoot: "Merkle Root",
    blockValidationCount: "區塊驗證數",
    blocksVerified: "個區塊已驗證",
    auditBreach: "審計鏈不一致，疑似竄改區塊",
    verifying: "驗證中...",
    verifyChain: "驗證鏈",
    simulateTamper: "模擬竄改",
    keyRotationFailed: "Key 輪替失敗",
    statusUpdateFailed: "訂閱狀態更新失敗",
    pauseFailed: "暫停失敗",
    resumeFailed: "恢復失敗",
    hijackSuccess: "人工介入指令已送出。",
    hijackFailed: "人工介入送出失敗",
    ledgerLoadFailed: "審計資料載入失敗",
    swarmInitialized: "Swarm 已初始化。",
    debateMessage: (currentAgent, targetAgent) => `共識回合：${currentAgent} 已派送更新至 ${targetAgent}`,
    blockLabel: "區塊",
    hashLabel: "雜湊",
    sessionLabel: "Session",
    stripeLabel: "Stripe",
    totalTokens: "總量",
    cost: "成本",
    tpmLimit: "5k tpm",
  },
  en: {
    intro: "Tenant isolation, billing limits, WebSocket interception, and SOC2 audit state in one operator console.",
    refresh: "Refresh",
    loadingTenants: "Loading tenants...",
    errorPrefix: "Error",
    none: "None",
    rotateTitle: "Rotate tenant API key",
    rotate: "Rotate",
    keyRotated: "Key rotated in memory.",
    active: "Active",
    freeze: "Freeze",
    cancel: "Cancel",
    wsLive: "WebSocket live",
    offlineSimulation: "Offline simulation",
    lastNode: "Last node",
    latency: "Latency",
    markupApplied: "Markup pricing applied",
    hitlTitle: "Inject human-in-the-loop input",
    close: "Close",
    hitlPlaceholder: "Type a response mock value or direct instruction to override native tool execution...",
    submitHijack: "Submit HITL Input",
    ledgerSubtitle: "SOC2 SHA-256 audit chain",
    healthy: "Healthy",
    tampered: "Tampered",
    merkleRoot: "Merkle Root",
    blockValidationCount: "Block validation count",
    blocksVerified: "blocks verified",
    auditBreach: "Audit chain mismatch detected at block",
    verifying: "Verifying...",
    verifyChain: "Verify chain",
    simulateTamper: "Simulate tamper",
    keyRotationFailed: "Key rotation failed",
    statusUpdateFailed: "Status update failed",
    pauseFailed: "Pause failed",
    resumeFailed: "Resume failed",
    hijackSuccess: "HITL command dispatched.",
    hijackFailed: "HITL dispatch failed",
    ledgerLoadFailed: "Audit ledger load failed",
    swarmInitialized: "Swarm initialized.",
    debateMessage: (currentAgent, targetAgent) => `Consensus round: ${currentAgent} dispatched update to ${targetAgent}`,
    blockLabel: "Block",
    hashLabel: "Hash",
    sessionLabel: "Session",
    stripeLabel: "Stripe",
    totalTokens: "Total",
    cost: "Cost",
    tpmLimit: "5k tpm",
  },
  ja: {
    intro: "テナント分離、課金制限、WebSocket 介入、SOC2 監査状態を一つの操作画面で管理します。",
    refresh: "更新",
    loadingTenants: "テナントを読み込み中...",
    errorPrefix: "エラー",
    none: "なし",
    rotateTitle: "テナント API key をローテーション",
    rotate: "ローテーション",
    keyRotated: "Key はメモリ上でローテーション済みです。",
    active: "有効",
    freeze: "凍結",
    cancel: "取消",
    wsLive: "WebSocket 接続中",
    offlineSimulation: "オフラインシミュレーション",
    lastNode: "最終ノード",
    latency: "レイテンシ",
    markupApplied: "加算価格を適用済み",
    hitlTitle: "人間介入入力を注入",
    close: "閉じる",
    hitlPlaceholder: "レスポンスの mock 値またはネイティブツール実行を上書きする指示を入力...",
    submitHijack: "HITL 入力を送信",
    ledgerSubtitle: "SOC2 SHA-256 監査チェーン",
    healthy: "正常",
    tampered: "改ざん",
    merkleRoot: "Merkle Root",
    blockValidationCount: "ブロック検証数",
    blocksVerified: "ブロック検証済み",
    auditBreach: "監査チェーン不一致を検出したブロック",
    verifying: "検証中...",
    verifyChain: "チェーン検証",
    simulateTamper: "改ざんを模擬",
    keyRotationFailed: "Key ローテーション失敗",
    statusUpdateFailed: "ステータス更新失敗",
    pauseFailed: "一時停止失敗",
    resumeFailed: "再開失敗",
    hijackSuccess: "HITL コマンドを送信しました。",
    hijackFailed: "HITL 送信失敗",
    ledgerLoadFailed: "監査データの読み込み失敗",
    swarmInitialized: "Swarm 初期化済み。",
    debateMessage: (currentAgent, targetAgent) => `合意ラウンド：${currentAgent} から ${targetAgent} へ更新を送信`,
    blockLabel: "ブロック",
    hashLabel: "ハッシュ",
    sessionLabel: "Session",
    stripeLabel: "Stripe",
    totalTokens: "合計",
    cost: "コスト",
    tpmLimit: "5k tpm",
  },
  fr: {
    intro: "Isolation des locataires, limites de facturation, interception WebSocket et audit SOC2 dans une console opérateur.",
    refresh: "Actualiser",
    loadingTenants: "Chargement des locataires...",
    errorPrefix: "Erreur",
    none: "Aucun",
    rotateTitle: "Faire tourner la clé API du locataire",
    rotate: "Rotation",
    keyRotated: "Clé remplacée en mémoire.",
    active: "Actif",
    freeze: "Geler",
    cancel: "Annuler",
    wsLive: "WebSocket actif",
    offlineSimulation: "Simulation hors ligne",
    lastNode: "Dernier noeud",
    latency: "Latence",
    markupApplied: "Tarification majorée appliquée",
    hitlTitle: "Injecter une entrée humaine",
    close: "Fermer",
    hitlPlaceholder: "Saisir une valeur mock ou une instruction directe pour remplacer l'exécution native...",
    submitHijack: "Envoyer l'entrée HITL",
    ledgerSubtitle: "Chaîne d'audit SOC2 SHA-256",
    healthy: "Sain",
    tampered: "Altéré",
    merkleRoot: "Merkle Root",
    blockValidationCount: "Nombre de blocs validés",
    blocksVerified: "blocs vérifiés",
    auditBreach: "Incohérence de chaîne détectée au bloc",
    verifying: "Vérification...",
    verifyChain: "Vérifier la chaîne",
    simulateTamper: "Simuler une altération",
    keyRotationFailed: "Rotation de clé échouée",
    statusUpdateFailed: "Mise à jour du statut échouée",
    pauseFailed: "Pause échouée",
    resumeFailed: "Reprise échouée",
    hijackSuccess: "Commande HITL envoyée.",
    hijackFailed: "Envoi HITL échoué",
    ledgerLoadFailed: "Chargement de l'audit échoué",
    swarmInitialized: "Swarm initialisé.",
    debateMessage: (currentAgent, targetAgent) => `Tour de consensus : ${currentAgent} a envoyé une mise à jour à ${targetAgent}`,
    blockLabel: "Bloc",
    hashLabel: "Hash",
    sessionLabel: "Session",
    stripeLabel: "Stripe",
    totalTokens: "Total",
    cost: "Coût",
    tpmLimit: "5k tpm",
  },
};

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function AdminDashboardView({ t, lang }: AdminDashboardViewProps) {
  const copy = ADMIN_COPY[lang];
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [errorTenants, setErrorTenants] = useState<string | null>(null);
  const [rotatedKeyInfo, setRotatedKeyInfo] = useState<{ [tenantId: string]: string }>({});
  const [actionStatus, setActionStatus] = useState<{ message: string; tone: "success" | "warning" | "danger" } | null>(null);

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
  }>({ latencyMs: 0, billingUsd: 0.0, lastMessage: "" });

  const [auditBlocks, setAuditBlocks] = useState<AuditBlock[]>([]);
  const [auditStatus, setAuditStatus] = useState<{
    valid: boolean;
    tampered_id: number | null;
    merkle_root: string;
  }>({ valid: true, tampered_id: null, merkle_root: "" });
  const [checkingLedger, setCheckingLedger] = useState(false);
  const [ledgerNodes, setLedgerNodes, onLedgerNodesChange] = useNodesState([]);
  const [ledgerEdges, setLedgerEdges, onLedgerEdgesChange] = useEdgesState([]);

  function setTimedActionStatus(message: string, tone: "success" | "warning" | "danger" = "success") {
    setActionStatus({ message, tone });
    window.setTimeout(() => setActionStatus(null), 3200);
  }

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
    } catch (err) {
      setErrorTenants(getErrorMessage(err));
    } finally {
      setLoadingTenants(false);
    }
  }, []);

  const fetchLedger = useCallback(async () => {
    setCheckingLedger(true);
    try {
      const statusResp = await fetch("http://localhost:8000/v1/audit/status", {
        headers: { "x-api-key": "key-admin" }
      });
      const statusData = await statusResp.json();
      
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
      logUiDiagnostic("Failed to load audit ledger data", err);
      setTimedActionStatus(`${copy.ledgerLoadFailed}: ${getErrorMessage(err)}`, "danger");
    } finally {
      setCheckingLedger(false);
    }
  }, [copy.ledgerLoadFailed]);

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
        void fetchTenants();
        setTimedActionStatus(copy.keyRotated);
      }
    } catch (err) {
      setTimedActionStatus(`${copy.keyRotationFailed}: ${getErrorMessage(err)}`, "danger");
    }
  };

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
        void fetchTenants();
        setTimedActionStatus(`${tenantId}: ${status}`);
      }
    } catch (err) {
      setTimedActionStatus(`${copy.statusUpdateFailed}: ${getErrorMessage(err)}`, "danger");
    }
  };

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
      setTimedActionStatus(`${copy.pauseFailed}: ${getErrorMessage(err)}`, "danger");
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
      setTimedActionStatus(`${copy.resumeFailed}: ${getErrorMessage(err)}`, "danger");
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
        setTimedActionStatus(copy.hijackSuccess);
        setHijackText("");
        setShowHijackInput(false);
      }
    } catch (err) {
      setTimedActionStatus(`${copy.hijackFailed}: ${getErrorMessage(err)}`, "danger");
    }
  };

  const handleReplayEvent = useCallback((event: SwarmReplayEvent) => {
    const activeNode = event.node_id || event.source || "CEO";
    const targetNode = event.target || "";
    setLastInteractedAgent(activeNode);
    setActiveTelemetry({
      latencyMs: event.latency_ms ?? 0,
      billingUsd: activeTelemetry.billingUsd,
      lastMessage: event.label,
    });
    setSwarmNodes(nodes =>
      nodes.map(node => ({
        ...node,
        style: {
          ...node.style,
          borderColor: node.id === activeNode ? "var(--accent)" : node.id === targetNode ? "var(--warning)" : "var(--border-c)",
          boxShadow: node.id === activeNode ? "var(--shadow-card), var(--ring)" : "var(--shadow-card)",
        },
      }))
    );
    setSwarmEdges(edges =>
      edges.map(edge => {
        const isActivePath = edge.source === activeNode || edge.target === targetNode;
        return {
          ...edge,
          animated: isActivePath,
          style: {
            ...edge.style,
            stroke: isActivePath ? "var(--accent)" : "var(--border-c)",
            strokeWidth: isActivePath ? 2.5 : 1.5,
          },
        };
      })
    );
  }, [activeTelemetry.billingUsd, setSwarmEdges, setSwarmNodes]);

  useEffect(() => {
    fetchTenants();
    fetchLedger();
  }, [fetchTenants, fetchLedger]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let mockInterval: ReturnType<typeof window.setInterval> | null = null;
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

            setSwarmNodes(nodes =>
              nodes.map(node => ({
                ...node,
                style: {
                  ...node.style,
                  borderColor: node.id === fromAgent ? "var(--accent)" : "var(--border-c)",
                  boxShadow: node.id === fromAgent ? "var(--shadow-card), var(--ring)" : "var(--shadow-card)"
                }
              }))
            );

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
        } catch {
          return;
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
          lastMessage: copy.debateMessage(currentAgent, targetAgent)
        });

        setSwarmNodes(nodes =>
          nodes.map(node => ({
            ...node,
            className: "",
            style: {
              ...node.style,
              borderColor: node.id === currentAgent ? "var(--accent)" : "var(--border-c)",
              boxShadow: node.id === currentAgent ? "var(--shadow-card), var(--ring)" : "var(--shadow-card)"
            }
          }))
        );

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
  }, [copy, selectedSessionId, wsConnected, swarmStatus]);

  useEffect(() => {
    if (auditBlocks.length === 0) {
      setLedgerNodes([]);
      setLedgerEdges([]);
      return;
    }

    const nodes = auditBlocks.map((block, i) => {
      const isTampered = !auditStatus.valid && block.id === auditStatus.tampered_id;
      return {
        id: `block-${block.id}`,
        data: {
          label: (
            <div className="flex flex-col text-[10px] text-left leading-relaxed">
              <span className="font-extrabold uppercase text-[9px]" style={{ color: isTampered ? "var(--danger)" : "var(--accent)" }}>
                {copy.blockLabel} #{block.id}
              </span>
              <span className="max-w-[130px] truncate font-bold t1">{block.event_type}</span>
              <span className="font-mono text-[8px] t3">{copy.hashLabel}: {block.current_hash.slice(0, 10)}...</span>
            </div>
          )
        },
        position: { x: i * 220 + 20, y: 60 },
        style: {
          background: "var(--bg-card)",
          borderColor: isTampered ? "var(--danger)" : "var(--border-c)",
          boxShadow: isTampered ? "var(--shadow-card), 0 0 0 3px color-mix(in srgb, var(--danger) 18%, transparent)" : "var(--shadow-card)",
          borderWidth: "1px",
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
          stroke: hasFailure ? "var(--danger)" : "var(--accent)",
          strokeWidth: 2
        }
      });
    }

    setLedgerNodes(nodes);
    setLedgerEdges(edges);
  }, [auditBlocks, auditStatus, copy.blockLabel, copy.hashLabel]);

  const simulateTamper = () => {
    setAuditStatus({
      valid: false,
      tampered_id: auditBlocks[1] ? auditBlocks[1].id : 1,
      merkle_root: "mock_tampered_merkle_root_001928"
    });
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto pr-2">
      <div className="flex justify-between items-center border-b pb-3" style={{ borderColor: "var(--border-c)" }}>
        <div>
          <h1 className="text-xl font-black t1">{t.adminConsole}</h1>
          <p className="text-xs t3 mt-0.5">{copy.intro}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {actionStatus && <StatusBadge tone={actionStatus.tone}>{actionStatus.message}</StatusBadge>}
          <Button
            onClick={() => {
              setLoadingTenants(true);
              void fetchTenants();
              void fetchLedger();
            }}
            variant="quiet"
            className="px-3 py-1.5"
          >
            {copy.refresh}
          </Button>
        </div>
      </div>

      <Surface as="section" elevated className="flex flex-col gap-3 p-4">
        <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{t.billingPlans}</h2>
        {loadingTenants ? (
          <div className="text-center text-xs py-4 t3">{copy.loadingTenants}</div>
        ) : errorTenants ? (
          <div className="text-center text-xs py-4" style={{ color: "var(--danger)" }}>{copy.errorPrefix}: {errorTenants}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tenants.map(tenant => (
              <Surface
                key={tenant.tenant_id}
                className="relative flex flex-col gap-3 p-4"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs font-black t1">{tenant.tenant_id}</span>
                    <p className="mt-0.5 max-w-[150px] truncate font-mono text-[9px] t3">
                      {copy.stripeLabel}: {tenant.stripe_subscription_id || copy.none}
                    </p>
                  </div>
                  <StatusBadge tone={toneForStatus(tenant.status)}>
                    {tenant.status}
                  </StatusBadge>
                </div>

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
                      title={copy.rotateTitle}
                    >
                      {copy.rotate}
                    </Button>
                  </div>
                  {rotatedKeyInfo[tenant.tenant_id] && (
                    <span className="text-[8px] font-bold" style={{ color: "var(--warning)" }}>{copy.keyRotated}</span>
                  )}
                </div>

                <div className="flex flex-col gap-1 text-[10px] mt-1">
                  <div className="flex justify-between font-bold">
                    <span className="t3 uppercase tracking-[0.08em]">{t.realTimeUsage}</span>
                    <span className="font-mono t3">
                      {tenant.tokens_last_minute} / {copy.tpmLimit}
                    </span>
                  </div>
                  <ProgressBar
                    value={(tenant.tokens_last_minute / 5000) * 100}
                    tone={tenant.tokens_last_minute >= 4000 ? "danger" : tenant.tokens_last_minute >= 2500 ? "warning" : "accent"}
                  />
                  <div className="mt-0.5 flex justify-between text-[8px] t3">
                    <span>{copy.totalTokens}: {tenant.total_tokens.toLocaleString()} tokens</span>
                    <span>{copy.cost}: ${tenant.total_cost_usd.toFixed(4)}</span>
                  </div>
                </div>

                {tenant.tenant_id !== "admin_tenant" && (
                  <div className="flex gap-1 border-t pt-2.5 mt-1 border-dashed" style={{ borderColor: "var(--border-c)" }}>
                    <Button
                      onClick={() => handleUpdateSubscription(tenant.tenant_id, "active")}
                      variant="primary"
                      className="flex-1 py-1 text-[9px]"
                    >
                      {copy.active}
                    </Button>
                    <Button
                      onClick={() => handleUpdateSubscription(tenant.tenant_id, "frozen")}
                      variant="warning"
                      className="flex-1 py-1 text-[9px]"
                    >
                      {copy.freeze}
                    </Button>
                    <Button
                      onClick={() => handleUpdateSubscription(tenant.tenant_id, "canceled")}
                      variant="danger"
                      className="flex-1 py-1 text-[9px]"
                    >
                      {copy.cancel}
                    </Button>
                  </div>
                )}
              </Surface>
            ))}
          </div>
        )}
      </Surface>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <Surface as="section" elevated className="relative flex min-h-[460px] flex-col gap-3 p-4 lg:col-span-7">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{t.liveInterceptor}</h2>
              <p className="text-[10px] t3 mt-0.5">{copy.sessionLabel}: {selectedSessionId}</p>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge tone={wsConnected ? "success" : "warning"}>
                {wsConnected ? copy.wsLive : copy.offlineSimulation}
              </StatusBadge>
            </div>
          </div>

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

            <Surface className="absolute bottom-3 left-3 z-10 flex max-w-[280px] flex-col gap-1 p-2.5 text-[9px]">
              <div className="flex justify-between font-bold t2">
                <span>{copy.lastNode}: <strong style={{ color: "var(--accent)" }}>{lastInteractedAgent || copy.none}</strong></span>
                <span>{copy.latency}: <strong style={{ color: "var(--accent)" }}>{activeTelemetry.latencyMs}ms</strong></span>
              </div>
              <p className="mt-0.5 truncate t3">{activeTelemetry.lastMessage || copy.swarmInitialized}</p>
              <div className="mt-1 flex items-center justify-between border-t pt-1 font-mono t3" style={{ borderColor: "var(--border-c)" }}>
                <span>{copy.markupApplied}</span>
                <span className="font-bold" style={{ color: "var(--success)" }}>${activeTelemetry.billingUsd.toFixed(4)} USD</span>
              </div>
            </Surface>
            <ReplayPlaybackWidget
              sessionId={selectedSessionId}
              lang={lang}
              onReplayEvent={handleReplayEvent}
            />
          </div>

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

          {showHijackInput && (
            <Surface className="absolute inset-x-4 bottom-16 z-20 flex flex-col gap-2 p-3">
              <div className="flex items-center justify-between border-b pb-1.5" style={{ borderColor: "var(--border-c)" }}>
                <span className="text-[10px] font-bold t2">{copy.hitlTitle}</span>
                <Button onClick={() => setShowHijackInput(false)} className="px-2 py-1 text-[10px]">{copy.close}</Button>
              </div>
              <textarea
                value={hijackText}
                onChange={e => setHijackText(e.target.value)}
                placeholder={copy.hitlPlaceholder}
                className="field-input h-16 resize-none rounded p-2 font-mono text-xs"
              />
              <Button
                onClick={handleHijackInput}
                variant="primary"
                className="w-full"
              >
                {copy.submitHijack}
              </Button>
            </Surface>
          )}
        </Surface>

        <Surface as="section" elevated className="relative flex min-h-[460px] flex-col gap-3 p-4 lg:col-span-5">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{t.ledgerVisualizer}</h2>
              <p className="text-[9px] t3 mt-0.5">{copy.ledgerSubtitle}</p>
            </div>
            <StatusBadge tone={auditStatus.valid ? "success" : "danger"}>
              {auditStatus.valid ? copy.healthy : copy.tampered}
            </StatusBadge>
          </div>

          <Surface className="flex flex-col gap-1 p-3 text-[10px]">
            <div className="flex justify-between">
              <span className="t3">{copy.merkleRoot}:</span>
              <span className="max-w-[170px] truncate font-mono t2" title={auditStatus.merkle_root}>
                {auditStatus.merkle_root || "0x00000000000000000000"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="t3">{copy.blockValidationCount}:</span>
              <span className="font-mono font-bold t2">{auditBlocks.length} {copy.blocksVerified}</span>
            </div>
            {auditStatus.tampered_id !== null && (
              <div className="mt-1.5 flex items-center gap-1.5 border-t pt-2 font-bold" style={{ borderColor: "color-mix(in srgb, var(--danger) 28%, transparent)", color: "var(--danger)" }}>
                <span className="text-[12px]">!</span>
                <span>{copy.auditBreach} #{auditStatus.tampered_id}.</span>
              </div>
            )}
          </Surface>

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

          <div className="flex gap-2">
            <Button
              onClick={fetchLedger}
              disabled={checkingLedger}
              className="flex-1"
            >
              {checkingLedger ? copy.verifying : copy.verifyChain}
            </Button>
            <Button
              onClick={simulateTamper}
              variant="danger"
              className="flex-1"
            >
              {copy.simulateTamper}
            </Button>
          </div>
        </Surface>
      </div>

      <SwarmGovernanceConsole
        lang={lang}
        onStatus={setTimedActionStatus}
      />
    </div>
  );
}
