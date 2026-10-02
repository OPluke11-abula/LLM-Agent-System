import { Link } from "react-router-dom";
import { ActivityLog } from "./ActivityLog";
import { NextActionRail } from "./NextActionRail";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  MetricTile,
  ProgressBar,
  StatusBadge,
  BentoCard,
  ShimmerButton,
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
    title: "Mission Control",
    eyebrow: "LAS LIVE OPERATIONS",
    subtitle: "拓撲、任務、驗證、風險與記憶訊號集中在第一視窗。",
    live: "即時拓撲",
    offline: "等待拓撲串流",
    activeMission: "主任務",
    verification: "驗證",
    risk: "風險",
    memory: "記憶",
    topology: "拓撲焦點",
    nextAction: "下一步",
    conductor: "Conductor trace",
    evidence: "Evidence refs",
    agents: "Agents",
    tasks: "Tasks",
    tokens: "Tokens",
    noTask: "沒有進行中任務，請從 Task Flow 選定下一個執行節點。",
    noTopology: "尚未收到 runtime topology。可先檢查 Task Flow 或啟動後端 stream。",
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

function nodePosition(index: number, total: number) {
  if (index === 0) return { x: 50, y: 50 };
  const angle = ((index - 1) / Math.max(1, total - 1)) * Math.PI * 2 - Math.PI / 2;
  return {
    x: 50 + Math.cos(angle) * 34,
    y: 50 + Math.sin(angle) * 31,
  };
}

function MissionTopology({ session, copy }: { session: TopologyState | null; copy: (typeof COPY)[Lang] }) {
  const nodes = session?.nodes.slice(0, 9) ?? [];
  const tone = signalTone(session);

  return (
    <BentoCard borderBeam={Boolean(session)} className="mission-focal relative min-h-[360px] overflow-hidden p-4 sm:p-5">
      <div className="relative z-10 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-1.5 text-xs font-medium text-[var(--accent)]">
            <Radio className="h-3.5 w-3.5" />
            <span>{copy.topology}</span>
          </div>
          <h2 className="mt-1 text-lg font-semibold t1">{session?.project_name ?? "LAS Runtime"}</h2>
          <p className="mt-1 max-w-xl text-xs leading-relaxed t2">{session?.summary ?? copy.noTopology}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge tone={tone}>{session ? copy.live : copy.offline}</StatusBadge>
          <Link
            to="/topology"
            className="quiet-button inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium"
          >
            <span>Graph</span>
            <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>

      <div className="relative z-10 mt-4 h-64 rounded-lg border border-[var(--border-c)] bg-[var(--bg-base)] flex items-center justify-center overflow-hidden">
        {nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 px-6 text-center">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-[var(--border-c)] bg-[var(--bg-card)] text-[var(--t3)]">
              <Network className="h-4 w-4" />
            </div>
            <div>
              <p className="text-xs font-medium text-[var(--t1)]">{copy.noTopology}</p>
              <p className="mt-0.5 text-[11px] text-[var(--t3)]">Active runtime nodes and execution DAG will appear here.</p>
            </div>
            <Link
              to="/tasks"
              className="quiet-button mt-1 inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium"
            >
              <GitFork className="h-3.5 w-3.5" />
              <span>Inspect Task Flow</span>
            </Link>
          </div>
        ) : (
          <div className="relative h-full w-full p-4">
            <svg className="absolute inset-0 h-full w-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
              {nodes.slice(1).map((node, index) => {
                const target = nodePosition(index + 1, nodes.length);
                return (
                  <line
                    key={node.id}
                    x1="50"
                    y1="50"
                    x2={target.x}
                    y2={target.y}
                    stroke="var(--border-strong)"
                    strokeDasharray="2 2"
                    strokeWidth="0.4"
                  />
                );
              })}
            </svg>
            {nodes.map((node, index) => {
              const position = nodePosition(index, nodes.length);
              const toneName = toneForStatus(node.status);
              return (
                <div
                  key={node.id}
                  className="mission-node absolute max-w-[9rem] rounded-md border px-2.5 py-1.5"
                  style={{
                    left: `${position.x}%`,
                    top: `${position.y}%`,
                    transform: "translate(-50%, -50%)",
                    borderColor: "var(--border-c)",
                  }}
                  title={node.description}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: `var(--${toneName === "danger" ? "danger" : toneName === "warning" ? "warning" : "accent"})` }} />
                    <p className="truncate text-xs font-medium t1">{node.title || node.node_type}</p>
                  </div>
                  <p className="mt-0.5 truncate text-[10px] font-mono t3">{node.assigned_agent || node.node_type}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </BentoCard>
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
            <CardTitle className="mt-1 text-sm font-semibold t1">{trace?.task_summary ?? event?.title ?? "No active trace"}</CardTitle>
          </div>
          <StatusBadge tone={trace?.risk_level === "high" ? "danger" : trace?.risk_level === "medium" ? "warning" : "accent"}>
            {trace?.risk_level ?? "standby"}
          </StatusBadge>
        </div>
      </CardHeader>
      <CardContent className="p-4 pt-2">
        <div className="grid grid-cols-3 gap-2">
          <MetricTile label={copy.tasks} value={total ? `${completed}/${total}` : "0"} />
          <MetricTile label={copy.evidence} value={trace?.evidence_refs?.length ?? 0} tone="accent" />
          <MetricTile label="Tests" value={trace?.impact_summary?.linked_test_count ?? 0} tone="success" />
        </div>
        <ProgressBar ariaLabel={copy.verification} className="mt-3" value={total ? (completed / total) * 100 : 0} tone={trace?.risk_level === "high" ? "danger" : "accent"} />
        <p className="mt-2.5 line-clamp-2 text-xs leading-relaxed t2">{trace?.decision_rationale ?? event?.description ?? "Runtime trace will appear after conductor planning."}</p>
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
  let badgeLabel = "clear";
  if (taskStats.running > 0) {
    badgeTone = "warning";
    badgeLabel = "running";
  } else if (taskStats.pending > 0) {
    badgeTone = "accent";
    badgeLabel = "queued";
  }

  return (
    <BentoCard className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-slate-400">{copy.activeMission}</p>
          <h2 className="mt-1 line-clamp-2 break-words text-sm font-semibold t1">
            {taskStats.nextTask?.description ?? copy.noTask}
          </h2>
        </div>
        <StatusBadge tone={badgeTone}>{badgeLabel}</StatusBadge>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <MetricTile label="Pending" value={taskStats.pending} tone="warning" />
        <MetricTile label="Running" value={taskStats.running} tone="accent" />
        <MetricTile label="Done" value={taskStats.completed} tone="success" />
      </div>
      <ProgressBar
        ariaLabel={copy.verification}
        className="mt-3"
        value={verificationScore}
        tone={verificationScore === 100 ? "success" : "accent"}
      />
      <p className="mt-2.5 break-all text-[11px] font-mono t3" title={workspace?.path}>
        {workspace?.name ?? activeWorkspaceId} · {workspace?.path || "default workspace"}
      </p>
    </BentoCard>
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
    <main className="mission-control relative h-full min-h-0 overflow-y-auto overflow-x-hidden">
      <div className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[320px] bg-[radial-gradient(ellipse_at_top,rgba(99,102,241,0.14)_0%,rgba(6,182,212,0.04)_45%,transparent_70%)] blur-3xl" />

      <div className="relative z-10 mx-auto flex max-w-[1480px] flex-col gap-4 pb-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-white/10 pb-3">
          <div>
            <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
              <span>FindAi Studio</span>
              <span>/</span>
              <span className="text-slate-300">{workspace?.name ?? "Default Workspace"}</span>
            </div>
            <h1 className="mt-0.5 text-xl font-bold tracking-tight t1">{copy.title}</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={session ? "success" : "neutral"} pulse={Boolean(session)}>
              {session ? copy.live : copy.offline}
            </StatusBadge>
            <Button type="button" variant="quiet" size="sm" disabled className="text-xs font-medium">
              {copy.verification}: {verificationScore}%
            </Button>
            <Link to="/topology" className="quiet-button inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium">
              <Network className="h-3.5 w-3.5" />
              <span>Topology</span>
            </Link>
            <Link to="/tasks">
              <ShimmerButton>
                <GitFork className="h-3.5 w-3.5" />
                <span>Task Flow</span>
                <ArrowRight className="h-3 w-3" />
              </ShimmerButton>
            </Link>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <MetricTile label={copy.agents} value={session?.stats.total_nodes ?? 0} tone={session ? "accent" : "neutral"} className="acrylic-surface acrylic-surface-hover transition-colors" />
          <MetricTile label={copy.tasks} value={taskStats.total} className="acrylic-surface acrylic-surface-hover transition-colors" />
          <MetricTile label={copy.tokens} value={(session?.stats.total_tokens ?? 0).toLocaleString()} className="acrylic-surface acrylic-surface-hover transition-colors" />
          <MetricTile label={copy.risk} value={session?.stats.errors ?? 0} tone={riskTone} className="acrylic-surface acrylic-surface-hover transition-colors" />
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
