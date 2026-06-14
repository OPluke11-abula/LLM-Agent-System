import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, StatusBadge, Surface, toneForStatus } from "./ui/primitives";
import type { Lang } from "../types";

type Tone = "success" | "warning" | "danger";
type VoteChoice = "approve" | "reject";

type VoteState = {
  node: string;
  role: string;
  vote: "approve" | "reject" | "pending";
};

type GovernanceProposal = {
  id: string;
  title: string;
  category: string;
  status: string;
  summary: string;
  votes: VoteState[];
};

type PromptRule = {
  id: string;
  category: string;
  title: string;
  before: string;
  after: string;
  weight: number;
};

type CalibrationLog = {
  id: string;
  timestamp: string;
  trigger: string;
  ruleId: string;
  result: string;
};

type AnomalyEvent = {
  id: string;
  timestamp: string;
  title: string;
  severity: "low" | "medium" | "high";
  mitigated: boolean;
  mitigationRule: string;
};

type CalibrationCopy = {
  title: string;
  subtitle: string;
  proposals: string;
  rules: string;
  diff: string;
  logs: string;
  anomalies: string;
  approve: string;
  reject: string;
  voting: string;
  pending: string;
  before: string;
  after: string;
  weight: string;
  trigger: string;
  mitigated: string;
  unmitigated: string;
  offline: string;
  loaded: string;
  voteSent: string;
  actionFailed: string;
};

const COPY: Record<Lang, CalibrationCopy> = {
  zh: {
    title: "Swarm Governance & Prompt Calibration",
    subtitle: "治理投票、PromptComposer 規則、校準 diff 與 AuditLedger anomaly timeline。",
    proposals: "Active Proposals",
    rules: "Prompt Rule Book",
    diff: "Calibration Diff",
    logs: "Optimization Log",
    anomalies: "Anomaly Timeline",
    approve: "Approve",
    reject: "Reject",
    voting: "投票中",
    pending: "Pending",
    before: "Pre-Calibrated Rule",
    after: "Post-Calibrated Rule",
    weight: "權重",
    trigger: "觸發",
    mitigated: "已緩解",
    unmitigated: "觀察中",
    offline: "Prompt governance 使用本地 fallback snapshot。",
    loaded: "Prompt governance 資料已載入。",
    voteSent: "治理投票已送出。",
    actionFailed: "操作失敗",
  },
  en: {
    title: "Swarm Governance & Prompt Calibration",
    subtitle: "Governance ballots, PromptComposer rules, calibration diffs, and AuditLedger anomaly timeline.",
    proposals: "Active Proposals",
    rules: "Prompt Rule Book",
    diff: "Calibration Diff",
    logs: "Optimization Log",
    anomalies: "Anomaly Timeline",
    approve: "Approve",
    reject: "Reject",
    voting: "Voting",
    pending: "Pending",
    before: "Pre-Calibrated Rule",
    after: "Post-Calibrated Rule",
    weight: "Weight",
    trigger: "Trigger",
    mitigated: "Mitigated",
    unmitigated: "Watching",
    offline: "Prompt governance is using a local fallback snapshot.",
    loaded: "Prompt governance data loaded.",
    voteSent: "Governance vote submitted.",
    actionFailed: "Action failed",
  },
  ja: {
    title: "Swarm Governance & Prompt Calibration",
    subtitle: "ガバナンス投票、PromptComposer ルール、校正 diff、AuditLedger anomaly timeline を表示します。",
    proposals: "Active Proposals",
    rules: "Prompt Rule Book",
    diff: "Calibration Diff",
    logs: "Optimization Log",
    anomalies: "Anomaly Timeline",
    approve: "Approve",
    reject: "Reject",
    voting: "投票中",
    pending: "Pending",
    before: "Pre-Calibrated Rule",
    after: "Post-Calibrated Rule",
    weight: "重み",
    trigger: "トリガー",
    mitigated: "緩和済み",
    unmitigated: "監視中",
    offline: "Prompt governance はローカル fallback snapshot を使用中。",
    loaded: "Prompt governance data loaded.",
    voteSent: "Governance vote submitted.",
    actionFailed: "操作失敗",
  },
  fr: {
    title: "Swarm Governance & Prompt Calibration",
    subtitle: "Scrutins de gouvernance, règles PromptComposer, diffs de calibration et timeline AuditLedger.",
    proposals: "Active Proposals",
    rules: "Prompt Rule Book",
    diff: "Calibration Diff",
    logs: "Optimization Log",
    anomalies: "Anomaly Timeline",
    approve: "Approve",
    reject: "Reject",
    voting: "Vote",
    pending: "Pending",
    before: "Pre-Calibrated Rule",
    after: "Post-Calibrated Rule",
    weight: "Poids",
    trigger: "Déclencheur",
    mitigated: "Mitigé",
    unmitigated: "Surveillance",
    offline: "Prompt governance utilise un snapshot local fallback.",
    loaded: "Prompt governance data loaded.",
    voteSent: "Governance vote submitted.",
    actionFailed: "Action échouée",
  },
};

const fallbackProposals: GovernanceProposal[] = [
  {
    id: "gov-prompt-184",
    title: "Tighten sandbox escalation prompt",
    category: "prompt calibration",
    status: "pending",
    summary: "Increase instruction weight for workspace-bound file operations after repeated sandbox denials.",
    votes: [
      { node: "CEO", role: "strategy", vote: "approve" },
      { node: "CTO", role: "architecture", vote: "approve" },
      { node: "Auditor", role: "risk", vote: "reject" },
      { node: "CFO", role: "budget", vote: "pending" },
    ],
  },
  {
    id: "gov-rule-221",
    title: "Budget-aware model routing rule",
    category: "rule update",
    status: "pending",
    summary: "Prefer low-cost tiers after quota pressure crosses the 90 percent alert boundary.",
    votes: [
      { node: "CEO", role: "strategy", vote: "approve" },
      { node: "CTO", role: "architecture", vote: "pending" },
      { node: "Auditor", role: "risk", vote: "pending" },
      { node: "CFO", role: "budget", vote: "approve" },
    ],
  },
];

const fallbackRules: PromptRule[] = [
  {
    id: "rule-safety-01",
    category: "Safety",
    title: "Sandbox boundary enforcement",
    before: "Reject destructive operations when target paths are unclear.",
    after: "Reject destructive operations when target paths are unclear. Require absolute path verification before recursive file operations.",
    weight: 0.92,
  },
  {
    id: "rule-cost-03",
    category: "Billing",
    title: "Quota pressure routing",
    before: "Use the requested model tier unless the runtime blocks dispatch.",
    after: "When quota pressure exceeds 90 percent, downscale non-critical tasks to gemini-2.5-flash and mark the action in telemetry.",
    weight: 0.76,
  },
  {
    id: "rule-latency-07",
    category: "Latency",
    title: "Anomaly-aware prompt compaction",
    before: "Compact context after major milestones.",
    after: "Compact context after major milestones or after latency anomaly windows exceed 2 seconds for two consecutive runs.",
    weight: 0.81,
  },
];

const fallbackLogs: CalibrationLog[] = [
  { id: "cal-1", timestamp: "10:16:42", trigger: "Latency Anomaly: 2.1s", ruleId: "rule-latency-07", result: "Prompt compaction threshold lowered." },
  { id: "cal-2", timestamp: "10:04:18", trigger: "Budget Alert: Quota 90% reached", ruleId: "rule-cost-03", result: "Auto-downscale instruction activated." },
  { id: "cal-3", timestamp: "09:58:03", trigger: "Sandbox Denial: recursive path unresolved", ruleId: "rule-safety-01", result: "Path verification weight increased." },
];

const fallbackAnomalies: AnomalyEvent[] = [
  { id: "anom-1", timestamp: "10:18:09", title: "Tool execution latency returned below 900ms", severity: "low", mitigated: true, mitigationRule: "rule-latency-07" },
  { id: "anom-2", timestamp: "10:03:55", title: "Budget alert threshold crossed", severity: "medium", mitigated: true, mitigationRule: "rule-cost-03" },
  { id: "anom-3", timestamp: "09:57:32", title: "Sandbox escalation denied unsafe target", severity: "high", mitigated: false, mitigationRule: "rule-safety-01" },
];

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function asString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
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

function mapVote(value: unknown): VoteState {
  const record = asRecord(value);
  const vote = asString(record.vote ?? record.choice, "pending").toLowerCase();
  return {
    node: asString(record.node ?? record.agent ?? record.node_id, "Agent"),
    role: asString(record.role, "cluster"),
    vote: vote === "approve" || vote === "reject" ? vote : "pending",
  };
}

function mapProposals(raw: unknown): GovernanceProposal[] {
  return readArray(raw, ["proposals", "pending"]).map((item, index) => {
    const record = asRecord(item);
    const votes = readArray(record.votes, ["votes"]).map(mapVote);
    return {
      id: asString(record.id ?? record.proposal_id, `proposal-${index + 1}`),
      title: asString(record.title, "Governance proposal"),
      category: asString(record.category ?? record.type, "governance"),
      status: asString(record.status, "pending"),
      summary: asString(record.summary ?? record.description, ""),
      votes: votes.length > 0 ? votes : fallbackProposals[0].votes,
    };
  });
}

function mapRules(raw: unknown): PromptRule[] {
  return readArray(raw, ["rules", "data"]).map((item, index) => {
    const record = asRecord(item);
    return {
      id: asString(record.id ?? record.rule_id, `rule-${index + 1}`),
      category: asString(record.category, "General"),
      title: asString(record.title ?? record.name, "Prompt rule"),
      before: asString(record.before ?? record.pre_calibrated ?? record.previous, ""),
      after: asString(record.after ?? record.post_calibrated ?? record.current, ""),
      weight: asNumber(record.weight ?? record.instruction_weight, 0),
    };
  });
}

function mapLogs(raw: unknown): CalibrationLog[] {
  return readArray(raw, ["logs", "calibrations", "history"]).map((item, index) => {
    const record = asRecord(item);
    return {
      id: asString(record.id, `calibration-${index + 1}`),
      timestamp: asString(record.timestamp ?? record.time, "--:--:--"),
      trigger: asString(record.trigger ?? record.exception, "Runtime signal"),
      ruleId: asString(record.rule_id ?? record.ruleId, "rule"),
      result: asString(record.result ?? record.summary, "Calibration recorded."),
    };
  });
}

function mapAnomalies(raw: unknown): AnomalyEvent[] {
  return readArray(raw, ["anomalies", "events", "logs"]).map((item, index) => {
    const record = asRecord(item);
    const severity = asString(record.severity, "medium").toLowerCase();
    return {
      id: asString(record.id ?? record.event_id, `anomaly-${index + 1}`),
      timestamp: asString(record.timestamp ?? record.time, "--:--:--"),
      title: asString(record.title ?? record.message ?? record.event_type, "AuditLedger anomaly"),
      severity: severity === "high" || severity === "low" ? severity : "medium",
      mitigated: asBoolean(record.mitigated ?? record.self_healed, false),
      mitigationRule: asString(record.mitigation_rule ?? record.rule_id, "pending"),
    };
  });
}

function changedLines(before: string, after: string) {
  const beforeLines = before.split(/\s+/).filter(Boolean);
  const afterLines = after.split(/\s+/).filter(Boolean);
  return {
    before: beforeLines,
    after: afterLines,
    changed: new Set(afterLines.filter((line, index) => beforeLines[index] !== line)),
  };
}

function voteTone(vote: VoteState["vote"]) {
  if (vote === "approve") return "success";
  if (vote === "reject") return "danger";
  return "warning";
}

function anomalyTone(severity: AnomalyEvent["severity"]) {
  if (severity === "high") return "danger";
  if (severity === "medium") return "warning";
  return "success";
}

export function PromptCalibrationDashboard({
  lang,
  onStatus,
}: {
  lang: Lang;
  onStatus: (message: string, tone?: Tone) => void;
}) {
  const copy = COPY[lang];
  const [proposals, setProposals] = useState<GovernanceProposal[]>(fallbackProposals);
  const [rules, setRules] = useState<PromptRule[]>(fallbackRules);
  const [logs, setLogs] = useState<CalibrationLog[]>(fallbackLogs);
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>(fallbackAnomalies);
  const [selectedProposalId, setSelectedProposalId] = useState(fallbackProposals[0].id);
  const [selectedRuleId, setSelectedRuleId] = useState(fallbackRules[0].id);
  const [voteLoading, setVoteLoading] = useState<VoteChoice | null>(null);

  const selectedProposal = proposals.find(proposal => proposal.id === selectedProposalId) ?? proposals[0];
  const selectedRule = rules.find(rule => rule.id === selectedRuleId) ?? rules[0];
  const diff = useMemo(() => changedLines(selectedRule.before, selectedRule.after), [selectedRule]);

  const loadCalibrationData = useCallback(async () => {
    const [proposalResult, rulesResult, anomalyResult] = await Promise.allSettled([
      fetchJson<unknown>("http://localhost:8000/v1/swarm/governance/proposals"),
      fetchJson<unknown>("http://localhost:8000/v1/swarm/governance/rules"),
      fetchJson<unknown>("http://localhost:8000/v1/audit/logs"),
    ]);

    let usedFallback = false;
    if (proposalResult.status === "fulfilled") {
      const nextProposals = mapProposals(proposalResult.value);
      setProposals(nextProposals.length > 0 ? nextProposals : fallbackProposals);
      setSelectedProposalId((nextProposals[0] ?? fallbackProposals[0]).id);
    } else {
      usedFallback = true;
      setProposals(fallbackProposals);
    }

    if (rulesResult.status === "fulfilled") {
      const record = asRecord(rulesResult.value);
      const nextRules = mapRules(rulesResult.value);
      const nextLogs = mapLogs(record.logs ?? record.calibrations ?? rulesResult.value);
      setRules(nextRules.length > 0 ? nextRules : fallbackRules);
      setLogs(nextLogs.length > 0 ? nextLogs : fallbackLogs);
      setSelectedRuleId((nextRules[0] ?? fallbackRules[0]).id);
    } else {
      usedFallback = true;
      setRules(fallbackRules);
      setLogs(fallbackLogs);
    }

    if (anomalyResult.status === "fulfilled") {
      const nextAnomalies = mapAnomalies(anomalyResult.value);
      setAnomalies(nextAnomalies.length > 0 ? nextAnomalies : fallbackAnomalies);
    } else {
      usedFallback = true;
      setAnomalies(fallbackAnomalies);
    }

    onStatus(usedFallback ? copy.offline : copy.loaded, usedFallback ? "warning" : "success");
  }, [copy.loaded, copy.offline, onStatus]);

  useEffect(() => {
    void loadCalibrationData();
  }, [loadCalibrationData]);

  async function castVote(choice: VoteChoice) {
    if (!selectedProposal) return;
    setVoteLoading(choice);
    try {
      await fetchJson<unknown>("http://localhost:8000/v1/swarm/governance/vote", {
        method: "POST",
        body: JSON.stringify({
          proposal_id: selectedProposal.id,
          vote: choice,
          node_id: "operator-console",
          signature: "operator-console-signed-vote",
        }),
      });
      onStatus(copy.voteSent);
      setProposals(current => current.map(proposal => proposal.id === selectedProposal.id
        ? {
          ...proposal,
          votes: [
            ...proposal.votes.filter(vote => vote.node !== "Operator"),
            { node: "Operator", role: "current", vote: choice },
          ],
        }
        : proposal));
    } catch (error) {
      onStatus(`${copy.actionFailed}: ${error instanceof Error ? error.message : String(error)}`, "danger");
    } finally {
      setVoteLoading(null);
    }
  }

  return (
    <Surface as="section" elevated className="flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xs font-black uppercase tracking-[0.14em] t1">{copy.title}</h2>
          <p className="mt-1 max-w-3xl text-xs t3">{copy.subtitle}</p>
        </div>
        <Button onClick={loadCalibrationData} variant="quiet">
          {copy.rules}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <Surface className="flex flex-col gap-3 p-3 xl:col-span-4">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.proposals}</h3>
          <div className="flex max-h-[310px] flex-col gap-2 overflow-y-auto pr-1">
            {proposals.map(proposal => (
              <Button
                key={proposal.id}
                type="button"
                onClick={() => setSelectedProposalId(proposal.id)}
                variant="quiet"
                className="w-full p-3 text-left"
                style={{
                  borderColor: proposal.id === selectedProposal.id ? "var(--accent)" : "var(--border-c)",
                  background: proposal.id === selectedProposal.id ? "var(--accent-bg)" : "var(--bg-muted)",
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold t1">{proposal.title}</p>
                    <p className="mt-1 text-[10px] t3">{proposal.category}</p>
                  </div>
                  <StatusBadge tone={toneForStatus(proposal.status)}>{proposal.status}</StatusBadge>
                </div>
                <p className="mt-2 line-clamp-2 text-[10px] t3">{proposal.summary}</p>
              </Button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Button onClick={() => castVote("approve")} disabled={voteLoading !== null} variant="primary">
              {voteLoading === "approve" ? copy.voting : copy.approve}
            </Button>
            <Button onClick={() => castVote("reject")} disabled={voteLoading !== null} variant="danger">
              {voteLoading === "reject" ? copy.voting : copy.reject}
            </Button>
          </div>
        </Surface>

        <Surface className="flex flex-col gap-3 p-3 xl:col-span-4">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">Consensus Voting Progress</h3>
          <div className="grid grid-cols-1 gap-2">
            {selectedProposal.votes.map(vote => (
              <div key={`${selectedProposal.id}-${vote.node}`} className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-lg border p-2" style={{ borderColor: "var(--border-c)" }}>
                <div className="min-w-0">
                  <p className="truncate font-mono text-xs font-semibold t1">{vote.node}</p>
                  <p className="text-[10px] t3">{vote.role}</p>
                </div>
                <StatusBadge tone={voteTone(vote.vote)}>{vote.vote === "pending" ? copy.pending : vote.vote}</StatusBadge>
              </div>
            ))}
          </div>
          <div className="mt-auto rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] t3">{selectedProposal.id}</p>
            <p className="mt-1 text-xs t2">{selectedProposal.summary}</p>
          </div>
        </Surface>

        <Surface className="flex flex-col gap-3 p-3 xl:col-span-4">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.rules}</h3>
          <div className="flex max-h-[310px] flex-col gap-2 overflow-y-auto pr-1">
            {rules.map(rule => (
              <Button
                key={rule.id}
                type="button"
                onClick={() => setSelectedRuleId(rule.id)}
                variant="quiet"
                className="w-full p-3 text-left"
                style={{
                  borderColor: rule.id === selectedRule.id ? "var(--accent)" : "var(--border-c)",
                  background: rule.id === selectedRule.id ? "var(--accent-bg)" : "var(--bg-muted)",
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-semibold t1">{rule.title}</p>
                    <p className="mt-1 text-[10px] t3">{rule.category}</p>
                  </div>
                  <span className="font-mono text-[10px] t2">{copy.weight} {rule.weight.toFixed(2)}</span>
                </div>
              </Button>
            ))}
          </div>
        </Surface>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
        <Surface className="flex flex-col gap-3 p-3 xl:col-span-7">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.diff}</h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="min-h-[170px] rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.before}</p>
              <p className="font-mono text-[11px] leading-relaxed t2">{selectedRule.before}</p>
            </div>
            <div className="min-h-[170px] rounded-lg border p-3" style={{ borderColor: "color-mix(in srgb, var(--accent) 36%, transparent)", background: "var(--bg-muted)" }}>
              <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.after}</p>
              <p className="font-mono text-[11px] leading-relaxed">
                {diff.after.map((word, index) => (
                  <span
                    key={`${word}-${index}`}
                    className="mr-1 rounded px-0.5"
                    style={{
                      color: diff.changed.has(word) ? "var(--accent-strong)" : "var(--t2)",
                      background: diff.changed.has(word) ? "var(--accent-bg)" : "transparent",
                    }}
                  >
                    {word}
                  </span>
                ))}
              </p>
            </div>
          </div>
        </Surface>

        <Surface className="flex flex-col gap-3 p-3 xl:col-span-5">
          <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.logs}</h3>
          <div className="flex max-h-[190px] flex-col gap-2 overflow-y-auto pr-1">
            {logs.map(log => (
              <div key={log.id} className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}>
                <div className="flex items-start justify-between gap-2">
                  <p className="font-mono text-[10px] t3">{log.timestamp}</p>
                  <StatusBadge tone="warning">{copy.trigger}</StatusBadge>
                </div>
                <p className="mt-1 text-xs font-semibold t1">{log.trigger}</p>
                <p className="mt-1 text-[10px] t3">{log.ruleId}: {log.result}</p>
              </div>
            ))}
          </div>
        </Surface>
      </div>

      <Surface className="flex flex-col gap-3 p-3">
        <h3 className="text-[10px] font-black uppercase tracking-[0.14em] t2">{copy.anomalies}</h3>
        <div className="grid grid-cols-1 gap-2 lg:grid-cols-3">
          {anomalies.map(anomaly => (
            <div key={anomaly.id} className="rounded-lg border p-3" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
              <div className="flex items-start justify-between gap-2">
                <p className="font-mono text-[10px] t3">{anomaly.timestamp}</p>
                <StatusBadge tone={anomalyTone(anomaly.severity)}>{anomaly.severity}</StatusBadge>
              </div>
              <p className="mt-2 text-xs font-semibold t1">{anomaly.title}</p>
              <div className="mt-3 flex items-center justify-between gap-2">
                <span className="truncate font-mono text-[10px] t3">{anomaly.mitigationRule}</span>
                <StatusBadge tone={anomaly.mitigated ? "success" : "warning"}>
                  {anomaly.mitigated ? copy.mitigated : copy.unmitigated}
                </StatusBadge>
              </div>
            </div>
          ))}
        </div>
      </Surface>
    </Surface>
  );
}
