import { Link } from "react-router-dom";
import { ActivityLog } from "./ActivityLog";
import { NextActionRail } from "./NextActionRail";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetricTile,
  ProgressBar,
  StatusBadge,
} from "./ui/primitives";
import { toneForStatus, type Tone } from "./ui/utils";
import { ArrowRight, GitFork, Network, Radio, Workflow } from "./ui/icons";
import { TokenModePanel } from "./TokenModePanel";
import type { ActivityLogEntry, AgentMemory, AgentTask, Lang, TopologyEvent, TopologyState, Workspace } from "../types";

type MissionControlViewProps = {
  memory: AgentMemory;
  workspaces: Workspace[];
  activeWorkspaceId: string;
  sessions: TopologyState[];
  lastUpdatedSessionId: string | null;
  activityEntries: ActivityLogEntry[];
  onClearActivityLog: () => void;
  lang: Lang;
};

type TaskStats = {
  total: number;
  pending: number;
  running: number;
  completed: number;
  nextTask: AgentTask | null;
};

const COPY: Record<Lang, {
  title: string;
  eyebrow: string;
  subtitle: string;
  live: string;
  offline: string;
  activeMission: string;
  verification: string;
  risk: string;
  memory: string;
  topology: string;
  nextAction: string;
  conductor: string;
  evidence: string;
  agents: string;
  tasks: string;
  tokens: string;
  noTask: string;
  noTopology: string;
}> = {
  zh: {
    title: "任務指揮總覽",
    eyebrow: "LAS 即時運作中樞",
    subtitle: "架構拓撲、任務進度、天梯驗證、風險評估與情境記憶集中呈現於第一視窗。",
    live: "即時拓撲串流",
    offline: "等待拓撲串流連線",
    activeMission: "核心進行中任務",
    verification: "驗證進度",
    risk: "風險缺陷",
    memory: "情境記憶",
    topology: "架構拓撲焦點",
    nextAction: "建議下一步行動",
    conductor: "編排追蹤軌跡",
    evidence: "驗證收據引用",
    agents: "代理人節點",
    tasks: "任務總數",
    tokens: "Token 消耗",
    noTask: "目前無執行中任務，請至任務圖譜選擇下一個執行節點。",
    noTopology: "尚未收到執行時拓撲串流。可檢查任務圖譜或確認後端服務已啟動。",
  },
  en: {
    title: "Mission Control",
    eyebrow: "LAS LIVE OPERATIONS",
    subtitle: "Topology, missions, verification, risk, and memory signals in the first viewport.",
    live: "Live topology",
    offline: "Waiting for topology stream",
    activeMission: "Active mission",
    verification: "Verification",
    risk: "Risk",
    memory: "Memory",
    topology: "Topology focus",
    nextAction: "Next action",
    conductor: "Conductor trace",
    evidence: "Evidence refs",
    agents: "Agents",
    tasks: "Tasks",
    tokens: "Tokens",
    noTask: "No running mission. Pick the next executable node from Task Flow.",
    noTopology: "No runtime topology received yet. Inspect Task Flow or start the backend stream.",
  },
  ja: {
    title: "Mission Control",
    eyebrow: "LAS LIVE OPERATIONS",
    subtitle: "トポロジー、任務、検証、リスク、メモリ信号を最初の画面に集約します。",
    live: "ライブトポロジー",
    offline: "トポロジーストリーム待機中",
    activeMission: "アクティブ任務",
    verification: "検証",
    risk: "リスク",
    memory: "メモリ",
    topology: "トポロジー焦点",
    nextAction: "次のアクション",
    conductor: "Conductor trace",
    evidence: "Evidence refs",
    agents: "Agents",
    tasks: "Tasks",
    tokens: "Tokens",
    noTask: "実行中の任務はありません。Task Flow から次のノードを選んでください。",
    noTopology: "runtime topology はまだ届いていません。Task Flow または backend stream を確認してください。",
  },
  fr: {
    title: "Mission Control",
    eyebrow: "LAS LIVE OPERATIONS",
    subtitle: "Topologie, missions, vérification, risque et mémoire dans la première vue.",
    live: "Topologie live",
    offline: "En attente du flux topology",
    activeMission: "Mission active",
    verification: "Vérification",
    risk: "Risque",
    memory: "Mémoire",
    topology: "Focus topologie",
    nextAction: "Action suivante",
    conductor: "Conductor trace",
    evidence: "Evidence refs",
    agents: "Agents",
    tasks: "Tasks",
    tokens: "Tokens",
    noTask: "Aucune mission active. Choisissez le prochain noeud dans Task Flow.",
    noTopology: "Aucune topologie runtime reçue. Inspectez Task Flow ou démarrez le flux backend.",
  },
};

function collectTaskStats(tasks: AgentTask[]): TaskStats {
  const stats: TaskStats = { total: 0, pending: 0, running: 0, completed: 0, nextTask: null };

  function visit(taskList: AgentTask[]) {
    for (const task of taskList) {
      stats.total += 1;
      if (task.status === "completed") stats.completed += 1;
      if (task.status === "in_progress") stats.running += 1;
      if (task.status === "pending") stats.pending += 1;
      if (!stats.nextTask && (task.status === "in_progress" || task.status === "pending")) stats.nextTask = task;
      visit(task.tasks ?? []);
    }
  }

  visit(tasks);
  return stats;
}

function latestSession(sessions: TopologyState[], lastUpdatedSessionId: string | null) {
  return sessions.find((session) => session.session_id === lastUpdatedSessionId) ?? sessions[0] ?? null;
}

function signalTone(session: TopologyState | null): Tone {
  if (!session) return "warning";
  if (session.stats.errors > 0) return "danger";
  if (session.stats.running > 0 || session.stats.pending > 0) return "accent";
  return "success";
}



function MissionTopology({ session, copy }: { session: TopologyState | null; copy: (typeof COPY)[Lang] }) {
  const nodes = session?.nodes.slice(0, 8) ?? [];
  const tone = signalTone(session);

  return (
    <Card className="mission-focal relative min-h-[360px] overflow-hidden p-4 sm:p-5">
      <div className="relative z-10 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-1.5 text-xs font-medium text-blue-400">
            <Radio className="h-3.5 w-3.5" />
            <span>{copy.topology}</span>
          </div>
          <h2 className="mt-1 text-base font-semibold t1">{session?.project_name ?? "LAS 執行時態"}</h2>
          <p className="mt-0.5 max-w-xl text-xs leading-relaxed t2">{session?.summary ?? copy.noTopology}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={tone}>{session ? copy.live : copy.offline}</StatusBadge>
          <Link
            to="/topology"
            className="quiet-button inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium"
          >
            <span>完整拓撲</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      <div className="relative z-10 mt-4 min-h-[220px] rounded-lg border border-[var(--border-c)] bg-[var(--bg-base)] p-3 overflow-hidden bg-[radial-gradient(rgba(255,255,255,0.05)_1px,transparent_1px)] [background-size:16px_16px]">
        {nodes.length === 0 ? (
          <div className="flex min-h-[200px] flex-col items-center justify-center gap-2 px-6 text-center">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-[var(--border-c)] bg-[var(--bg-card)] text-[var(--t3)]">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-medium text-[var(--t1)]">{copy.noTopology}</p>
              <p className="mt-0.5 text-[11px] text-[var(--t3)]">即時運作節點與執行 DAG 將即時呈現於此處。</p>
            </div>
            <Link
              to="/tasks"
              className="quiet-button mt-1 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium"
            >
              <GitFork className="h-3.5 w-3.5" />
              <span>檢視任務圖譜</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {nodes.map((node) => {
              const toneName = toneForStatus(node.status);
              return (
                <div
                  key={node.id}
                  className="group relative flex flex-col justify-between rounded-md border border-[var(--border-c)] bg-[var(--bg-card)] p-3 transition-colors hover:border-[var(--border-strong)]"
                  title={node.description}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] text-[var(--t3)] truncate">
                      {node.assigned_agent || "AGENT"}
                    </span>
                    <span
                      className="h-1.5 w-1.5 rounded-full shrink-0"
                      style={{ background: `var(--${toneName === "danger" ? "danger" : toneName === "warning" ? "warning" : "accent"})` }}
                    />
                  </div>
                  <div className="mt-2">
                    <p className="truncate text-xs font-semibold t1 group-hover:text-blue-400 transition-colors">
                      {node.title || node.node_type}
                    </p>
                    <p className="mt-1 line-clamp-2 text-[10px] text-[var(--t3)] leading-relaxed">
                      {node.description || "執行管線節點"}
                    </p>
                  </div>
                  <div className="mt-2.5 pt-2 border-t border-[var(--border-c)] flex items-center justify-between text-[10px] font-mono text-[var(--t3)]">
                    <span>{node.node_type}</span>
                    <span className="capitalize text-zinc-400">{node.status}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

function ConductorPanel({ event, copy }: { event: TopologyEvent | null; copy: (typeof COPY)[Lang] }) {
  const trace = event?.payload.conductor_trace;
  const completed = trace?.subtasks.filter((task) => task.status === "completed" || task.status === "done").length ?? 0;
  const total = trace?.subtasks.length ?? 0;

  return (
    <Card className="conductor-panel">
      <CardHeader className="p-4 pb-2">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-medium text-[var(--accent)]">
              <Workflow className="h-3.5 w-3.5" />
              <span>{copy.conductor}</span>
            </div>
            <CardTitle className="mt-1 text-sm font-semibold t1">{trace?.task_summary ?? event?.title ?? "目前無活躍編排軌跡"}</CardTitle>
          </div>
          <StatusBadge tone={trace?.risk_level === "high" ? "danger" : trace?.risk_level === "medium" ? "warning" : "accent"}>
            {trace?.risk_level ?? "待命"}
          </StatusBadge>
        </div>
      </CardHeader>
      <CardContent className="p-4 pt-2">
        <div className="grid grid-cols-3 gap-2">
          <MetricTile label={copy.tasks} value={total ? `${completed}/${total}` : "0"} />
          <MetricTile label={copy.evidence} value={trace?.evidence_refs?.length ?? 0} tone="accent" />
          <MetricTile label="測試驗證" value={trace?.impact_summary?.linked_test_count ?? 0} tone="success" />
        </div>
        <ProgressBar ariaLabel={copy.verification} className="mt-3" value={total ? (completed / total) * 100 : 0} tone={trace?.risk_level === "high" ? "danger" : "accent"} />
        <p className="mt-2.5 line-clamp-2 text-xs leading-relaxed t2">{trace?.decision_rationale ?? event?.description ?? "編排規劃生成後，將於此處即時呈現決策鏈與驗證路徑。"}</p>
      </CardContent>
    </Card>
  );
}

function computeMissionSnapshot(
  memory: AgentMemory,
  workspaces: any[],
  activeWorkspaceId: string | null,
  sessions: TopologyState[],
  lastUpdatedSessionId: string | null
) {
  const session = latestSession(sessions, lastUpdatedSessionId);
  const taskStats = collectTaskStats(memory.tasks);
  const workspace = workspaces.find((item) => item.id === activeWorkspaceId);
  const activeEvent =
    session?.nodes.find((node) =>
      ["running", "in_process", "awaiting_approval", "review"].includes(node.status)
    ) ?? session?.nodes[0] ?? null;
  const riskTone = signalTone(session);
  const verificationScore = taskStats.total
    ? Math.round((taskStats.completed / taskStats.total) * 100)
    : 0;

  return {
    session,
    taskStats,
    workspace,
    activeEvent,
    riskTone,
    verificationScore,
  };
}

function ActiveMissionCard({
  taskStats,
  verificationScore,
  workspace,
  activeWorkspaceId,
  copy,
}: {
  taskStats: any;
  verificationScore: number;
  workspace: any;
  activeWorkspaceId: string | null;
  copy: typeof COPY[Lang];
}) {
  let badgeTone: "warning" | "accent" | "success" = "success";
  let badgeLabel = "正常";
  if (taskStats.running > 0) {
    badgeTone = "warning";
    badgeLabel = "執行中";
  } else if (taskStats.pending > 0) {
    badgeTone = "accent";
    badgeLabel = "排隊中";
  }

  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-[var(--t3)]">{copy.activeMission}</p>
          <h2 className="mt-1 line-clamp-2 break-words text-sm font-semibold t1">
            {taskStats.nextTask?.description ?? copy.noTask}
          </h2>
        </div>
        <StatusBadge tone={badgeTone}>{badgeLabel}</StatusBadge>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <MetricTile label="待處理" value={taskStats.pending} tone="warning" />
        <MetricTile label="執行中" value={taskStats.running} tone="accent" />
        <MetricTile label="已完成" value={taskStats.completed} tone="success" />
      </div>
      <ProgressBar
        ariaLabel={copy.verification}
        className="mt-3"
        value={verificationScore}
        tone={verificationScore === 100 ? "success" : "accent"}
      />
      <p className="mt-2.5 break-all text-[11px] font-mono t3" title={workspace?.path}>
        {workspace?.name ?? activeWorkspaceId} · {workspace?.path || "預設工作區"}
      </p>
    </Card>
  );
}

export function MissionControlView({
  memory,
  workspaces,
  activeWorkspaceId,
  sessions,
  lastUpdatedSessionId,
  activityEntries,
  onClearActivityLog,
  lang,
}: MissionControlViewProps) {
  const copy = COPY[lang];
  const {
    session,
    taskStats,
    workspace,
    activeEvent,
    riskTone,
    verificationScore,
  } = computeMissionSnapshot(memory, workspaces, activeWorkspaceId, sessions, lastUpdatedSessionId);

  return (
    <main className="mission-control relative h-full min-h-0 overflow-y-auto overflow-x-hidden p-4 md:p-6">
      <div className="relative z-10 mx-auto flex max-w-[1480px] flex-col gap-4 pb-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-[var(--border-c)] pb-3.5">
          <div>
            <div className="flex items-center gap-1.5 text-xs text-[var(--t3)] font-mono">
              <span>LAS 控制中樞</span>
              <span>/</span>
              <span className="text-[var(--t2)]">{workspace?.name ?? "預設工作區"}</span>
            </div>
            <h1 className="mt-1 text-lg font-bold tracking-tight t1">{copy.title}</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={session ? "success" : "neutral"} pulse={Boolean(session)}>
              {session ? copy.live : copy.offline}
            </StatusBadge>
            <span className="inline-flex items-center rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-2.5 py-1 text-xs font-mono text-[var(--t2)]">
              {copy.verification}: {verificationScore}%
            </span>
            <Link to="/topology" className="quiet-button inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium">
              <Network className="h-3.5 w-3.5" />
              <span>架構拓撲</span>
            </Link>
            <Link to="/tasks" className="primary-button inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium">
              <GitFork className="h-3.5 w-3.5" />
              <span>任務圖譜</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricTile label={copy.agents} value={session?.stats.total_nodes ?? 0} tone={session ? "accent" : "neutral"} />
          <MetricTile label={copy.tasks} value={taskStats.total} />
          <MetricTile label={copy.tokens} value={(session?.stats.total_tokens ?? 0).toLocaleString()} />
          <MetricTile label={copy.risk} value={session?.stats.errors ?? 0} tone={riskTone} />
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
          <MissionTopology session={session} copy={copy} />
          <div className="grid gap-4">
            <ActiveMissionCard
              taskStats={taskStats}
              verificationScore={verificationScore}
              workspace={workspace}
              activeWorkspaceId={activeWorkspaceId}
              copy={copy}
            />

            <TokenModePanel session={session} nextTask={taskStats.nextTask} lang={lang} compact />

            <NextActionRail
              lang={lang}
              taskStats={taskStats}
              session={session}
              activeEvent={activeEvent}
              verificationScore={verificationScore}
            />
          </div>
        </div>

        <div className="grid min-h-[280px] gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(360px,0.55fr)]">
          <ConductorPanel event={activeEvent} copy={copy} />
          <ActivityLog entries={activityEntries.slice(0, 8)} lang={lang} onClear={onClearActivityLog} />
        </div>
      </div>
    </main>
  );
}
