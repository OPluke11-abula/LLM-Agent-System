
import { BentoCard, StatusBadge, Button } from "../ui/primitives";
import { cx } from "../ui/utils";
import { Users } from "../ui/icons";
import type { TaskDetailResponse } from "./types";

interface CommitteeDebateCardProps {
  taskDetail: TaskDetailResponse;
  lang?: string;
  onTriggerDebate: () => void;
  loading: boolean;
}

function PillarsScoreGrid({ sc }: { sc: any }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <div className="p-3 rounded-lg border border-white/10 bg-black/40 space-y-1">
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">🏛️ Architectural Integrity</span>
          <span className="font-mono font-bold text-indigo-300">
            {(sc.architectural_integrity * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full"
            style={{ width: `${Math.min(100, sc.architectural_integrity * 100)}%` }}
          />
        </div>
      </div>

      <div className="p-3 rounded-lg border border-white/10 bg-black/40 space-y-1">
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">🛡️ Security Assurance</span>
          <span className="font-mono font-bold text-emerald-300">
            {(sc.security_assurance * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full"
            style={{ width: `${Math.min(100, sc.security_assurance * 100)}%` }}
          />
        </div>
      </div>

      <div className="p-3 rounded-lg border border-white/10 bg-black/40 space-y-1">
        <div className="flex justify-between text-[11px]">
          <span className="text-slate-400">🧪 Test Thoroughness</span>
          <span className="font-mono font-bold text-sky-300">
            {(sc.test_thoroughness * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full bg-sky-500 rounded-full"
            style={{ width: `${Math.min(100, sc.test_thoroughness * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function DeliberationTurnsStream({ rounds }: { rounds?: any[] }) {
  if (!rounds || rounds.length === 0) return null;

  return (
    <div className="space-y-2 pt-2 border-t border-white/5 max-h-72 overflow-y-auto pr-1">
      <div className="text-[11px] font-mono text-slate-400 font-bold uppercase">
        Committee Deliberation Stream:
      </div>
      {rounds.flatMap((r) => r.turns || []).map((turn: any) => (
        <div
          key={`turn-${turn.speaker_role}-${turn.round_index}-${turn.turn_index}`}
          className="text-xs p-2.5 rounded bg-white/[0.03] border border-white/5 space-y-1"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono font-bold text-indigo-300 text-[11px]">
              [{turn.speaker_role.toUpperCase()}] R{turn.round_index} T{turn.turn_index}
            </span>
            {turn.score_impact !== 0 && (
              <span
                className={cx(
                  "text-[10px] font-mono",
                  turn.score_impact < 0 ? "text-rose-400" : "text-emerald-400"
                )}
              >
                {turn.score_impact > 0 ? `+${turn.score_impact}` : turn.score_impact}
              </span>
            )}
          </div>
          <p className="text-slate-300 text-xs leading-relaxed">{turn.content}</p>
          {turn.reasoning_content && (
            <details className="text-[11px] font-mono text-indigo-300/80 bg-indigo-950/30 rounded p-2 border border-indigo-500/20 my-1">
              <summary className="cursor-pointer font-bold text-[10px] text-indigo-400 select-none">
                🧠 Thinking Process ({turn.reasoning_tokens || 0} tokens)
              </summary>
              <div className="pt-1.5 whitespace-pre-wrap text-slate-400 text-[10px] leading-normal font-sans">
                {turn.reasoning_content}
              </div>
            </details>
          )}
          {turn.critique_points && turn.critique_points.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {turn.critique_points.map((cp: string) => (
                <span
                  key={`cp-${cp.slice(0, 24)}`}
                  className="text-[10px] font-mono bg-indigo-500/10 text-indigo-300 px-1.5 py-0.5 rounded border border-indigo-500/20"
                >
                  • {cp}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function DissentingOpinionsAlert({ dissenting }: { dissenting?: string[] }) {
  if (!dissenting || dissenting.length === 0) return null;

  return (
    <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200 space-y-1">
      <div className="font-bold font-mono text-[11px]">⚠️ Dissenting Objections Recorded:</div>
      {dissenting.map((d: string) => (
        <div key={`dissent-${d.slice(0, 32)}`} className="font-mono text-[11px]">• {d}</div>
      ))}
    </div>
  );
}

function ConveneDebatePrompt({
  lang,
  loading,
  onTriggerDebate,
}: {
  lang?: string;
  loading: boolean;
  onTriggerDebate: () => void;
}) {
  return (
    <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <Users className="h-5 w-5 text-indigo-400 shrink-0" />
        <div>
          <div className="text-xs font-bold text-white">
            {lang === "zh" ? "多 Agent 專家委員會 (Phase 85)" : "Multi-Agent Specialist Committee (P85)"}
          </div>
          <div className="text-[11px] text-slate-400">
            {lang === "zh"
              ? "在架構審批前由架構師、資安與 QA Agent 進行交叉辯論與共識記分"
              : "Convene cross-functional personas to deliberate and enrich the mutation plan"}
          </div>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={loading}
        onClick={onTriggerDebate}
        className="border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10 shrink-0"
      >
        {loading ? "Deliberating..." : "Convene Committee Debate"}
      </Button>
    </div>
  );
}

export function CommitteeDebateCard({
  taskDetail,
  lang,
  onTriggerDebate,
  loading,
}: CommitteeDebateCardProps) {
  const debate = taskDetail.committee_debate || taskDetail.result?.committee_debate;

  if (debate) {
    const sc = debate.consensus_scorecard;
    const isApproved = sc.decision === "CONSENSUS_APPROVED";

    return (
      <BentoCard className="border-indigo-500/40 bg-indigo-500/5 shadow-[0_0_24px_rgba(99,102,241,0.12)]">
        <div className="p-5 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">
                    {lang === "zh" ? "多 Agent 專家委員會辯論與共識記分卡" : "Multi-Agent Committee Consensus Scorecard"}
                  </h3>
                  <span className="rounded-full border border-indigo-500/30 bg-indigo-500/20 px-2 py-0.5 text-[10px] font-mono text-indigo-300">
                    Phase 85
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {lang === "zh"
                    ? "由架構師、資安審計師、QA 工程師協同評審，於架構關卡前消除盲點與合規風險"
                    : "Architect, Security Auditor & QA Engineer deliberate to eliminate blind spots prior to Gate"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <StatusBadge tone={isApproved ? "success" : "danger"}>
                {sc.decision}
              </StatusBadge>
              <span className="text-xs font-mono font-bold text-white bg-black/40 border border-white/10 px-2.5 py-1 rounded">
                {(sc.composite_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <PillarsScoreGrid sc={sc} />

          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-400 font-mono text-[11px]">Members:</span>
            {debate.committee_members.map((m: string) => (
              <span
                key={m}
                className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[11px] font-mono text-slate-300"
              >
                @{m}
              </span>
            ))}
            <span className="text-[10px] text-slate-500 ml-auto font-mono flex items-center gap-2">
              {sc.total_reasoning_tokens !== undefined && sc.total_reasoning_tokens > 0 && (
                <span className="text-purple-300 bg-purple-500/10 border border-purple-500/20 px-1.5 py-0.5 rounded">
                  🧠 {sc.total_reasoning_tokens} thinking tokens
                </span>
              )}
              <span>{debate.duration_ms}ms · {debate.rounds?.length || 1} round(s)</span>
            </span>
          </div>

          <DeliberationTurnsStream rounds={debate.rounds} />
          <DissentingOpinionsAlert dissenting={sc.dissenting_opinions} />
        </div>
      </BentoCard>
    );
  }

  if (taskDetail.result?.current_stage !== "COMPLETED") {
    return (
      <ConveneDebatePrompt
        lang={lang}
        loading={loading}
        onTriggerDebate={onTriggerDebate}
      />
    );
  }

  return null;
}
