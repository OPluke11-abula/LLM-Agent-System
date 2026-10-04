
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

function PillarsScoreGrid({ sc, lang }: { sc: any; lang?: string }) {
  const isZh = lang === "zh";
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)] space-y-1.5">
        <div className="flex justify-between text-[11px]">
          <span className="text-[var(--t2)]">{isZh ? "🏛️ 架構完整性" : "🏛️ Architectural Integrity"}</span>
          <span className="font-mono font-bold text-[var(--t1)]">
            {(sc.architectural_integrity * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-[var(--border-c)] overflow-hidden">
          <div
            className="h-full bg-[var(--accent)] rounded-full"
            style={{ width: `${Math.min(100, sc.architectural_integrity * 100)}%` }}
          />
        </div>
      </div>

      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)] space-y-1.5">
        <div className="flex justify-between text-[11px]">
          <span className="text-[var(--t2)]">{isZh ? "🛡️ 資安保證" : "🛡️ Security Assurance"}</span>
          <span className="font-mono font-bold text-emerald-400">
            {(sc.security_assurance * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-[var(--border-c)] overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full"
            style={{ width: `${Math.min(100, sc.security_assurance * 100)}%` }}
          />
        </div>
      </div>

      <div className="p-3 rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)] space-y-1.5">
        <div className="flex justify-between text-[11px]">
          <span className="text-[var(--t2)]">{isZh ? "🧪 測試嚴謹度" : "🧪 Test Thoroughness"}</span>
          <span className="font-mono font-bold text-sky-400">
            {(sc.test_thoroughness * 100).toFixed(0)}%
          </span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-[var(--border-c)] overflow-hidden">
          <div
            className="h-full bg-sky-500 rounded-full"
            style={{ width: `${Math.min(100, sc.test_thoroughness * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function DeliberationTurnsStream({ rounds, lang }: { rounds?: any[]; lang?: string }) {
  if (!rounds || rounds.length === 0) return null;
  const isZh = lang === "zh";

  return (
    <div className="space-y-2 pt-2 border-t border-[var(--border-c)] max-h-72 overflow-y-auto pr-1">
      <div className="text-[11px] font-mono text-[var(--t3)] font-semibold">
        {isZh ? "專家委員會審議串流：" : "Committee Deliberation Stream:"}
      </div>
      {rounds.flatMap((r) => r.turns || []).map((turn: any) => (
        <div
          key={`turn-${turn.speaker_role}-${turn.round_index}-${turn.turn_index}`}
          className="text-xs p-2.5 rounded-md bg-[var(--bg-muted)] border border-[var(--border-c)] space-y-1"
        >
          <div className="flex items-center justify-between">
            <span className="font-mono font-bold text-[var(--accent)] text-[11px]">
              [{turn.speaker_role.toUpperCase()}] R{turn.round_index} T{turn.turn_index}
            </span>
            {turn.score_impact !== 0 && (
              <span
                className={cx(
                  "text-[10px] font-mono font-semibold",
                  turn.score_impact < 0 ? "text-rose-400" : "text-emerald-400"
                )}
              >
                {turn.score_impact > 0 ? `+${turn.score_impact}` : turn.score_impact}
              </span>
            )}
          </div>
          <p className="text-[var(--t2)] text-xs leading-relaxed">{turn.content}</p>
          {turn.reasoning_content && (
            <details className="text-[11px] font-mono text-[var(--t2)] bg-[var(--bg-card)] rounded p-2 border border-[var(--border-c)] my-1">
              <summary className="cursor-pointer font-semibold text-[10px] text-[var(--accent)] select-none">
                🧠 {isZh ? "深度思考過程" : "Thinking Process"} ({turn.reasoning_tokens || 0} tokens)
              </summary>
              <div className="pt-1.5 whitespace-pre-wrap text-[var(--t3)] text-[10px] leading-normal font-sans">
                {turn.reasoning_content}
              </div>
            </details>
          )}
          {turn.critique_points && turn.critique_points.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {turn.critique_points.map((cp: string) => (
                <span
                  key={`cp-${cp.slice(0, 24)}`}
                  className="text-[10px] font-mono bg-[var(--bg-card)] text-[var(--t2)] px-1.5 py-0.5 rounded border border-[var(--border-c)]"
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

function DissentingOpinionsAlert({ dissenting, lang }: { dissenting?: string[]; lang?: string }) {
  if (!dissenting || dissenting.length === 0) return null;
  const isZh = lang === "zh";

  return (
    <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3 text-xs text-rose-300 space-y-1">
      <div className="font-semibold font-mono text-[11px] text-rose-400">
        ⚠️ {isZh ? "紀錄異議與保留意見：" : "Dissenting Objections Recorded:"}
      </div>
      {dissenting.map((d: string) => (
        <div key={`dissent-${d.slice(0, 32)}`} className="font-mono text-[11px] text-rose-300">• {d}</div>
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
  const isZh = lang === "zh";
  return (
    <div className="rounded-lg border border-[var(--border-c)] bg-[var(--bg-card)] p-4 flex flex-col sm:flex-row items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <Users className="h-5 w-5 text-[var(--accent)] shrink-0" />
        <div>
          <div className="text-xs font-semibold text-[var(--t1)]">
            {isZh ? "多 Agent 專家委員會 (Phase 85)" : "Multi-Agent Specialist Committee (P85)"}
          </div>
          <div className="text-[11px] text-[var(--t3)]">
            {isZh
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
        className="shrink-0 text-xs"
      >
        {loading ? (isZh ? "專家審議中..." : "Deliberating...") : (isZh ? "召開專家委員會辯論" : "Convene Committee Debate")}
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
  const isZh = lang === "zh";

  if (debate) {
    const sc = debate.consensus_scorecard;
    const isApproved = sc.decision === "CONSENSUS_APPROVED";

    return (
      <BentoCard className="border-[var(--border-c)] bg-[var(--bg-card)]">
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--bg-muted)] text-[var(--accent)] border border-[var(--border-c)]">
                <Users className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-[var(--t1)]">
                    {isZh ? "多 Agent 專家委員會辯論與共識記分卡" : "Multi-Agent Committee Consensus Scorecard"}
                  </h3>
                  <span className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-2 py-0.5 text-[10px] font-mono text-[var(--t2)]">
                    Phase 85
                  </span>
                </div>
                <p className="text-xs text-[var(--t3)] mt-0.5">
                  {isZh
                    ? "由架構師、資安審計師、QA 工程師協同評審，於架構關卡前消除盲點與合規風險"
                    : "Architect, Security Auditor & QA Engineer deliberate to eliminate blind spots prior to Gate"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <StatusBadge tone={isApproved ? "success" : "danger"}>
                {sc.decision}
              </StatusBadge>
              <span className="text-xs font-mono font-bold text-[var(--t1)] bg-[var(--bg-muted)] border border-[var(--border-c)] px-2.5 py-1 rounded-md">
                {(sc.composite_score * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          <PillarsScoreGrid sc={sc} lang={lang} />

          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-[var(--t3)] font-mono text-[11px]">{isZh ? "成員：" : "Members:"}</span>
            {debate.committee_members.map((m: string) => (
              <span
                key={m}
                className="rounded border border-[var(--border-c)] bg-[var(--bg-muted)] px-2 py-0.5 text-[11px] font-mono text-[var(--t2)]"
              >
                @{m}
              </span>
            ))}
            <span className="text-[10px] text-[var(--t3)] ml-auto font-mono flex items-center gap-2">
              {sc.total_reasoning_tokens !== undefined && sc.total_reasoning_tokens > 0 && (
                <span className="text-[var(--accent)] bg-[var(--bg-muted)] border border-[var(--border-c)] px-1.5 py-0.5 rounded">
                  🧠 {sc.total_reasoning_tokens} thinking tokens
                </span>
              )}
              <span>{debate.duration_ms}ms · {debate.rounds?.length || 1} round(s)</span>
            </span>
          </div>

          <DeliberationTurnsStream rounds={debate.rounds} lang={lang} />
          <DissentingOpinionsAlert dissenting={sc.dissenting_opinions} lang={lang} />
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
