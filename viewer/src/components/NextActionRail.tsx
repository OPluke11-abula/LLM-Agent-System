import { Link } from "react-router-dom";
import { StatusBadge, Surface, cx } from "./ui/primitives";
import type { AgentTask, Lang, TopologyEvent, TopologyState } from "../types";

type ActionTone = "accent" | "success" | "warning" | "danger" | "neutral";
type ActionStatus = "unavailable" | "ready" | "running" | "failed" | "completed";

type TaskStats = {
  total: number;
  pending: number;
  running: number;
  completed: number;
  nextTask: AgentTask | null;
};

type NextActionRailProps = {
  lang: Lang;
  taskStats: TaskStats;
  session: TopologyState | null;
  activeEvent: TopologyEvent | null;
  verificationScore: number;
};

type RailAction = {
  id: string;
  label: string;
  body: string;
  expected: string;
  command: string;
  fallback: string;
  route: string;
  tone: ActionTone;
  status: ActionStatus;
};

const COPY: Record<Lang, {
  title: string;
  subtitle: string;
  expected: string;
  command: string;
  fallback: string;
  labels: Record<"verify" | "topology" | "impact" | "handoff" | "governance" | "syncPap", string>;
  bodies: Record<"verify" | "topology" | "impact" | "handoff" | "governance" | "syncPap", string>;
  expectedText: Record<"verify" | "topology" | "impact" | "handoff" | "governance" | "syncPap", string>;
  fallbackText: Record<"verify" | "topology" | "impact" | "handoff" | "governance" | "syncPap", string>;
  statuses: Record<ActionStatus, string>;
}> = {
  zh: {
    title: "Next Best Action",
    subtitle: "依照任務、拓撲、驗證與風險狀態排序。",
    expected: "Expected",
    command: "Command",
    fallback: "Failure follow-up",
    labels: {
      verify: "驗證工作區",
      topology: "檢查拓撲焦點",
      impact: "顯示影響符號",
      handoff: "建立 handoff",
      governance: "檢查治理風險",
      syncPap: "同步 PAP contract",
    },
    bodies: {
      verify: "執行主要 gate，確認測試、PAP contract、viewer build 與 smoke checks。",
      topology: "開啟 runtime graph，定位目前 agent、等待節點或失敗節點。",
      impact: "查看 conductor trace 的 code graph refs、linked tests 與 evidence 摘要。",
      handoff: "收斂變更檔案、驗證結果、決策與下一個 agent 的讀取順序。",
      governance: "檢查錯誤、approval gate、安全控制與 audit 狀態。",
      syncPap: "確認 LAS 與 PAP schema/tool manifest 的同步狀態。",
    },
    expectedText: {
      verify: "得到可引用的 PASS 或第一個 failing gate。",
      topology: "看到 active node、edge 與 conductor trace 的關聯。",
      impact: "找出 impacted symbols、linked tests 與需要先讀的 evidence。",
      handoff: "產出下一輪可直接接手的摘要。",
      governance: "確認是否需要人工審核、修復或暫停。",
      syncPap: "PAP validator 能回報 contract 是否一致。",
    },
    fallbackText: {
      verify: "若失敗，先打開最新 failure 並回到 Task Flow 修第一個 gate。",
      topology: "若沒有 stream，先啟動 backend 或回 Task Flow 確認任務狀態。",
      impact: "若沒有 graph refs，先執行 code graph impact 或查看 memory。",
      handoff: "若資訊不足，先補驗證命令、changed files 與 unresolved risk。",
      governance: "若有高風險，先停在 approval gate，不要推進外部狀態。",
      syncPap: "若 contract 不一致，先修 manifest/schema 再跑 repo verify。",
    },
    statuses: { unavailable: "unavailable", ready: "ready", running: "running", failed: "failed", completed: "complete" },
  },
  en: {
    title: "Next Best Action",
    subtitle: "Ranked from task, topology, verification, and risk state.",
    expected: "Expected",
    command: "Command",
    fallback: "Failure follow-up",
    labels: {
      verify: "Verify workspace",
      topology: "Inspect topology focus",
      impact: "Show impacted symbols",
      handoff: "Create handoff",
      governance: "Review governance risk",
      syncPap: "Sync PAP contract",
    },
    bodies: {
      verify: "Run the main gate across tests, PAP contracts, viewer build, and smoke checks.",
      topology: "Open the runtime graph and locate the current agent, waiting node, or failure node.",
      impact: "Review conductor trace code graph refs, linked tests, and evidence summary.",
      handoff: "Collect changed files, verification results, decisions, and next-agent read order.",
      governance: "Check errors, approval gates, safety controls, and audit state.",
      syncPap: "Confirm LAS stays aligned with PAP schema and tool manifest contracts.",
    },
    expectedText: {
      verify: "You get a citeable PASS or the first failing gate.",
      topology: "You see the active node, edge, and conductor trace relationship.",
      impact: "You identify impacted symbols, linked tests, and evidence to read first.",
      handoff: "You produce a summary another agent can resume from.",
      governance: "You know whether review, repair, or pause is required.",
      syncPap: "The PAP validator reports whether contracts are aligned.",
    },
    fallbackText: {
      verify: "If it fails, open the latest failure and fix the first gate in Task Flow.",
      topology: "If no stream exists, start the backend or confirm task state in Task Flow.",
      impact: "If graph refs are missing, run code graph impact or inspect memory.",
      handoff: "If context is thin, add checks, changed files, and unresolved risk first.",
      governance: "If risk is high, stay at the approval gate before external-state work.",
      syncPap: "If contracts drift, fix manifest/schema before repo verify.",
    },
    statuses: { unavailable: "unavailable", ready: "ready", running: "running", failed: "failed", completed: "complete" },
  },
  ja: {
    title: "Next Best Action",
    subtitle: "task、topology、検証、risk 状態から優先順位付けします。",
    expected: "Expected",
    command: "Command",
    fallback: "Failure follow-up",
    labels: {
      verify: "Workspace を検証",
      topology: "Topology focus を確認",
      impact: "影響 symbol を表示",
      handoff: "Handoff 作成",
      governance: "Governance risk 確認",
      syncPap: "PAP contract 同期",
    },
    bodies: {
      verify: "tests、PAP contract、viewer build、smoke checks の main gate を実行します。",
      topology: "runtime graph を開き、現在の agent、待機 node、失敗 node を特定します。",
      impact: "conductor trace の code graph refs、linked tests、evidence summary を確認します。",
      handoff: "変更ファイル、検証結果、判断、次 agent の読む順序をまとめます。",
      governance: "errors、approval gates、安全制御、audit state を確認します。",
      syncPap: "LAS と PAP schema/tool manifest contract の同期を確認します。",
    },
    expectedText: {
      verify: "引用可能な PASS または最初の failing gate が得られます。",
      topology: "active node、edge、conductor trace の関係が見えます。",
      impact: "impacted symbols、linked tests、先に読む evidence が分かります。",
      handoff: "別 agent が再開できる summary を作れます。",
      governance: "review、repair、pause の必要性が分かります。",
      syncPap: "PAP validator が contract 一致状況を返します。",
    },
    fallbackText: {
      verify: "失敗時は latest failure を開き、Task Flow で最初の gate を修正。",
      topology: "stream が無ければ backend 起動か Task Flow の状態確認。",
      impact: "graph refs が無ければ code graph impact か memory を確認。",
      handoff: "情報不足なら checks、changed files、risk を先に補完。",
      governance: "high risk なら external-state 前に approval gate で停止。",
      syncPap: "contract drift があれば manifest/schema 修正後 repo verify。",
    },
    statuses: { unavailable: "unavailable", ready: "ready", running: "running", failed: "failed", completed: "complete" },
  },
  fr: {
    title: "Next Best Action",
    subtitle: "Priorisé depuis tâches, topologie, vérification et risque.",
    expected: "Expected",
    command: "Command",
    fallback: "Failure follow-up",
    labels: {
      verify: "Vérifier le workspace",
      topology: "Inspecter la topologie",
      impact: "Voir les symbols impactés",
      handoff: "Créer un handoff",
      governance: "Revoir le risque",
      syncPap: "Sync PAP contract",
    },
    bodies: {
      verify: "Exécute le gate principal: tests, PAP contracts, viewer build et smoke checks.",
      topology: "Ouvre le graphe runtime et localise agent courant, node en attente ou échec.",
      impact: "Revoit code graph refs, linked tests et résumé evidence du conductor trace.",
      handoff: "Collecte fichiers modifiés, vérifications, décisions et ordre de lecture.",
      governance: "Vérifie erreurs, approval gates, contrôles de sécurité et audit state.",
      syncPap: "Confirme l'alignement LAS avec PAP schema et tool manifest.",
    },
    expectedText: {
      verify: "Un PASS citable ou le premier failing gate.",
      topology: "Le lien active node, edge et conductor trace est visible.",
      impact: "Symbols impactés, linked tests et evidence à lire en premier.",
      handoff: "Un résumé exploitable par un autre agent.",
      governance: "Savoir s'il faut review, repair ou pause.",
      syncPap: "Le validator PAP indique si les contracts sont alignés.",
    },
    fallbackText: {
      verify: "Si échec, ouvrir latest failure puis corriger le premier gate.",
      topology: "Sans stream, démarrer backend ou confirmer Task Flow.",
      impact: "Sans graph refs, lancer code graph impact ou inspecter memory.",
      handoff: "Si contexte faible, ajouter checks, changed files et risk.",
      governance: "Si high risk, rester à l'approval gate avant état externe.",
      syncPap: "Si drift, corriger manifest/schema avant repo verify.",
    },
    statuses: { unavailable: "unavailable", ready: "ready", running: "running", failed: "failed", completed: "complete" },
  },
};

function statusTone(status: ActionStatus, fallbackTone: ActionTone): ActionTone {
  if (status === "failed") return "danger";
  if (status === "running") return "warning";
  if (status === "completed") return "success";
  if (status === "unavailable") return "neutral";
  return fallbackTone;
}

function buildActions({ lang, taskStats, session, activeEvent, verificationScore }: NextActionRailProps): RailAction[] {
  const copy = COPY[lang];
  const trace = activeEvent?.payload.conductor_trace;
  const impactCount =
    trace?.impact_summary?.impacted_symbol_count ??
    trace?.code_graph_refs?.length ??
    0;
  const riskLevel = trace?.risk_level?.toLowerCase();
  const hasHighRisk = riskLevel === "high" || (session?.stats.errors ?? 0) > 0;

  const actions: RailAction[] = [
    {
      id: "verify",
      label: copy.labels.verify,
      body: copy.bodies.verify,
      expected: copy.expectedText.verify,
      command: ".\\scripts\\verify.cmd",
      fallback: copy.fallbackText.verify,
      route: "/tasks",
      tone: "success",
      status: taskStats.total === 0 ? "unavailable" : verificationScore === 100 ? "completed" : taskStats.running > 0 ? "running" : "ready",
    },
    {
      id: "topology",
      label: copy.labels.topology,
      body: copy.bodies.topology,
      expected: copy.expectedText.topology,
      command: "open /topology",
      fallback: copy.fallbackText.topology,
      route: "/topology",
      tone: "accent",
      status: !session ? "unavailable" : session.stats.errors > 0 ? "failed" : session.stats.running > 0 || session.stats.pending > 0 ? "running" : "ready",
    },
    {
      id: "impact",
      label: copy.labels.impact,
      body: copy.bodies.impact,
      expected: copy.expectedText.impact,
      command: "python -m agent_workspace.skills.tool_codebase_memory code_detect_change_impact",
      fallback: copy.fallbackText.impact,
      route: "/memory",
      tone: "accent",
      status: impactCount > 0 ? "ready" : "unavailable",
    },
    {
      id: "governance",
      label: copy.labels.governance,
      body: copy.bodies.governance,
      expected: copy.expectedText.governance,
      command: "open /admin",
      fallback: copy.fallbackText.governance,
      route: "/admin",
      tone: "warning",
      status: hasHighRisk ? "failed" : riskLevel === "medium" || activeEvent?.status === "awaiting_approval" ? "ready" : "ready",
    },
    {
      id: "handoff",
      label: copy.labels.handoff,
      body: copy.bodies.handoff,
      expected: copy.expectedText.handoff,
      command: "handoff: collect changed files, checks, decisions, next reads",
      fallback: copy.fallbackText.handoff,
      route: "/tasks",
      tone: "neutral",
      status: taskStats.nextTask ? "ready" : "unavailable",
    },
    {
      id: "sync-pap",
      label: copy.labels.syncPap,
      body: copy.bodies.syncPap,
      expected: copy.expectedText.syncPap,
      command: "python agent_workspace/pap_validate.py .agent/agent.md",
      fallback: copy.fallbackText.syncPap,
      route: "/settings",
      tone: "accent",
      status: "ready",
    },
  ];

  return actions.sort((left, right) => {
    const rank: Record<ActionStatus, number> = { failed: 0, running: 1, ready: 2, unavailable: 3, completed: 4 };
    return rank[left.status] - rank[right.status];
  });
}

export function NextActionRail(props: NextActionRailProps) {
  const copy = COPY[props.lang];
  const actions = buildActions(props).slice(0, 4);
  const primaryAction = actions[0];

  return (
    <Surface as="aside" className="next-action-rail p-4" data-testid="next-action-rail" aria-label={copy.title}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.title}</p>
          <p className="mt-1 text-[11px] leading-relaxed t2">{copy.subtitle}</p>
        </div>
        <StatusBadge tone={statusTone(primaryAction.status, primaryAction.tone)}>
          {copy.statuses[primaryAction.status]}
        </StatusBadge>
      </div>

      <div className="mt-3 space-y-2">
        {actions.map((action, index) => {
          const tone = statusTone(action.status, action.tone);
          const unavailable = action.status === "unavailable";
          const body = (
            <>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-xs font-semibold t1">{action.label}</p>
                  <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed t2">{action.body}</p>
                </div>
                <StatusBadge tone={tone}>{copy.statuses[action.status]}</StatusBadge>
              </div>
              <div className="next-action-detail mt-3 grid gap-2">
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.12em] t3">{copy.expected}</p>
                  <p className="mt-1 text-[10px] leading-relaxed t2">{action.expected}</p>
                </div>
                <pre className="next-action-command truncate rounded-md px-2 py-1.5 text-[10px] t2" title={action.command}>{action.command}</pre>
                <p className="text-[10px] leading-relaxed t3">
                  <span className="font-semibold t2">{copy.fallback}: </span>{action.fallback}
                </p>
              </div>
            </>
          );

          if (unavailable) {
            return (
              <div
                key={action.id}
                className={cx("next-action-card next-action-card-unavailable", index === 0 && "next-action-card-primary")}
                aria-disabled="true"
              >
                {body}
              </div>
            );
          }

          return (
            <Link
              key={action.id}
              to={action.route}
              className={cx("next-action-card block", index === 0 && "next-action-card-primary")}
            >
              {body}
            </Link>
          );
        })}
      </div>
    </Surface>
  );
}
