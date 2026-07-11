import { Link } from "react-router-dom";
import { ActivityLog } from "./ActivityLog";
import { NextActionRail } from "./NextActionRail";
import { Button, MetricTile, ProgressBar, StatusBadge, Surface, toneForStatus } from "./ui/primitives";
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

function signalTone(session: TopologyState | null) {
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
    <Surface elevated className="mission-focal relative min-h-[360px] overflow-hidden p-4 sm:p-5">
      <div className="relative z-10 flex items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.topology}</p>
          <h2 className="mt-1 text-2xl font-semibold t1">{session?.project_name ?? "LAS Runtime"}</h2>
          <p className="mt-2 max-w-xl text-xs leading-relaxed t2">{session?.summary ?? copy.noTopology}</p>
        </div>
        <StatusBadge tone={tone}>{session ? copy.live : copy.offline}</StatusBadge>
      </div>

      <div className="mission-radar relative z-10 mt-5 h-64 rounded-xl border" style={{ borderColor: "var(--border-c)" }}>
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" role="img" aria-label={copy.topology}>
          <defs>
            <radialGradient id="missionGlow" cx="50%" cy="50%" r="52%">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.28" />
              <stop offset="62%" stopColor="var(--signal-violet)" stopOpacity="0.11" />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width="100" height="100" rx="8" fill="url(#missionGlow)" />
          {[18, 30, 42].map((radius) => (
            <circle key={radius} cx="50" cy="50" r={radius} fill="none" stroke="var(--border-c)" strokeWidth="0.35" />
          ))}
          {nodes.slice(1).map((node, index) => {
            const target = nodePosition(index + 1, nodes.length);
            return (
              <line
                key={node.id}
                x1="50"
                y1="50"
                x2={target.x}
                y2={target.y}
                stroke={node.status === "error" ? "var(--danger)" : "var(--accent)"}
                strokeOpacity={node.status === "error" ? 0.58 : 0.34}
                strokeWidth="0.55"
              />
            );
          })}
        </svg>

        {nodes.length === 0 ? (
          <div className="absolute inset-0 flex items-center justify-center px-5 text-center text-xs font-medium t3">
            {copy.noTopology}
          </div>
        ) : (
          nodes.map((node, index) => {
            const position = nodePosition(index, nodes.length);
            const toneName = toneForStatus(node.status);
            return (
              <div
                key={node.id}
                className="mission-node absolute max-w-[8.5rem] rounded-lg border px-2.5 py-2"
                style={{
                  left: `${position.x}%`,
                  top: `${position.y}%`,
                  transform: "translate(-50%, -50%)",
                  borderColor: `color-mix(in srgb, var(--${toneName === "danger" ? "danger" : toneName === "warning" ? "warning" : "accent"}) 36%, transparent)`,
                }}
                title={node.description}
              >
                <p className="truncate text-[10px] font-bold t1">{node.title || node.node_type}</p>
                <p className="mt-0.5 truncate text-[9px] font-mono t3">{node.assigned_agent || node.node_type}</p>
              </div>
            );
          })
        )}
      </div>
    </Surface>
  );
}

function ConductorPanel({ event, copy }: { event: TopologyEvent | null; copy: (typeof COPY)[Lang] }) {
  const trace = event?.payload.conductor_trace;
  const completed = trace?.subtasks.filter((task) => task.status === "completed" || task.status === "done").length ?? 0;
  const total = trace?.subtasks.length ?? 0;

  return (
    <Surface as="section" className="p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.conductor}</p>
          <h3 className="mt-1 text-sm font-semibold t1">{trace?.task_summary ?? event?.title ?? "No active trace"}</h3>
        </div>
        <StatusBadge tone={trace?.risk_level === "high" ? "danger" : trace?.risk_level === "medium" ? "warning" : "accent"}>
          {trace?.risk_level ?? "standby"}
        </StatusBadge>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <MetricTile label={copy.tasks} value={total ? `${completed}/${total}` : "0"} />
        <MetricTile label={copy.evidence} value={trace?.evidence_refs?.length ?? 0} tone="accent" />
        <MetricTile label="Tests" value={trace?.impact_summary?.linked_test_count ?? 0} tone="success" />
      </div>
      <ProgressBar ariaLabel={copy.verification} className="mt-4" value={total ? (completed / total) * 100 : 0} tone={trace?.risk_level === "high" ? "danger" : "accent"} />
      <p className="mt-3 line-clamp-3 text-xs leading-relaxed t2">{trace?.decision_rationale ?? event?.description ?? "Runtime trace will appear after conductor planning."}</p>
    </Surface>
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
  const session = latestSession(sessions, lastUpdatedSessionId);
  const taskStats = collectTaskStats(memory.tasks);
  const workspace = workspaces.find((item) => item.id === activeWorkspaceId);
  const activeEvent = session?.nodes.find((node) => ["running", "in_process", "awaiting_approval", "review"].includes(node.status)) ?? session?.nodes[0] ?? null;
  const riskTone = signalTone(session);
  const verificationScore = taskStats.total ? Math.round((taskStats.completed / taskStats.total) * 100) : 0;

  return (
    <main className="mission-control h-full min-h-0 overflow-y-auto">
      <div className="mx-auto flex max-w-[1480px] flex-col gap-4 pb-6">
        <section className="mission-hero control-surface overflow-hidden px-4 py-4 sm:px-5">
          <div className="relative z-10 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.18em] accent-text">{copy.eyebrow}</p>
              <h1 className="mt-2 max-w-4xl text-4xl font-semibold leading-none t1 sm:text-5xl">{copy.title}</h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed t2">{copy.subtitle}</p>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:w-[33rem]">
              <MetricTile label={copy.agents} value={session?.stats.total_nodes ?? 0} tone={session ? "accent" : "neutral"} />
              <MetricTile label={copy.tasks} value={taskStats.total} />
              <MetricTile label={copy.tokens} value={(session?.stats.total_tokens ?? 0).toLocaleString()} />
              <MetricTile label={copy.risk} value={session?.stats.errors ?? 0} tone={riskTone} />
            </div>
          </div>
        </section>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
          <MissionTopology session={session} copy={copy} />
          <div className="grid gap-4">
            <Surface as="section" elevated className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] t3">{copy.activeMission}</p>
                  <h2 className="mt-1 line-clamp-2 break-words text-base font-semibold t1">{taskStats.nextTask?.description ?? copy.noTask}</h2>
                </div>
                <StatusBadge tone={taskStats.running > 0 ? "warning" : taskStats.pending > 0 ? "accent" : "success"}>
                  {taskStats.running > 0 ? "running" : taskStats.pending > 0 ? "queued" : "clear"}
                </StatusBadge>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2">
                <MetricTile label="Pending" value={taskStats.pending} tone="warning" />
                <MetricTile label="Running" value={taskStats.running} tone="accent" />
                <MetricTile label="Done" value={taskStats.completed} tone="success" />
              </div>
              <ProgressBar ariaLabel={copy.verification} className="mt-4" value={verificationScore} tone={verificationScore === 100 ? "success" : "accent"} />
              <p className="mt-3 break-all text-[10px] font-mono t3" title={workspace?.path}>{workspace?.name ?? activeWorkspaceId} · {workspace?.path || "default workspace"}</p>
            </Surface>

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

        <div className="grid min-h-[320px] gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(360px,0.55fr)]">
          <ConductorPanel event={activeEvent} copy={copy} />
          <ActivityLog entries={activityEntries.slice(0, 8)} lang={lang} onClear={onClearActivityLog} />
        </div>

        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="quiet" disabled>{copy.verification}: {verificationScore}%</Button>
          <Link to="/topology" className="quiet-button rounded-lg px-3 py-1.5 text-xs font-semibold">{copy.live}</Link>
          <Link to="/tasks" className="primary-button rounded-lg px-3 py-1.5 text-xs font-semibold">{copy.activeMission}</Link>
        </div>
      </div>
    </main>
  );
}
