import { MetricTile, ProgressBar, StatusBadge, Surface } from "./ui/primitives";
import type { AgentTask, Lang, TopologyState } from "../types";

type TokenModePanelProps = {
  session: TopologyState | null;
  nextTask: AgentTask | null;
  lang: Lang;
  compact?: boolean;
};

type TokenModeCopy = {
  title: string;
  eyebrow: string;
  context: string;
  contributors: string;
  nextAction: string;
  profile: string;
  handoff: string;
  handoffRecommended: string;
  handoffClear: string;
  noContributors: string;
  noAction: string;
  estimated: string;
};

const COPY: Record<Lang, TokenModeCopy> = {
  zh: {
    title: "Token 工作模式",
    eyebrow: "ADVISORY CONTEXT CONTROL",
    context: "上下文估算",
    contributors: "主要貢獻者",
    nextAction: "建議下一步",
    profile: "驗證設定",
    handoff: "交接門檻",
    handoffRecommended: "建議現在交接",
    handoffClear: "目前可繼續",
    noContributors: "尚無 token 貢獻資料。",
    noAction: "先從 Task Flow 選擇下一個可執行節點。",
    estimated: "估算",
  },
  en: {
    title: "Token work mode",
    eyebrow: "ADVISORY CONTEXT CONTROL",
    context: "Context estimate",
    contributors: "Largest contributors",
    nextAction: "Recommended next action",
    profile: "Verification profile",
    handoff: "Handoff gate",
    handoffRecommended: "Handoff recommended now",
    handoffClear: "Continue within budget",
    noContributors: "No token contributors reported yet.",
    noAction: "Pick the next executable node from Task Flow.",
    estimated: "Estimated",
  },
  ja: {
    title: "Token ワークモード",
    eyebrow: "ADVISORY CONTEXT CONTROL",
    context: "コンテキスト推定",
    contributors: "主な貢献者",
    nextAction: "推奨される次の操作",
    profile: "検証プロファイル",
    handoff: "ハンドオフゲート",
    handoffRecommended: "今すぐハンドオフを推奨",
    handoffClear: "予算内で継続",
    noContributors: "Token の貢献データはまだありません。",
    noAction: "Task Flow から次の実行ノードを選んでください。",
    estimated: "推定",
  },
  fr: {
    title: "Mode de travail token",
    eyebrow: "ADVISORY CONTEXT CONTROL",
    context: "Estimation du contexte",
    contributors: "Contributeurs principaux",
    nextAction: "Action recommandée",
    profile: "Profil de vérification",
    handoff: "Seuil de relais",
    handoffRecommended: "Relais recommandé maintenant",
    handoffClear: "Continuer dans le budget",
    noContributors: "Aucun contributeur token signalé.",
    noAction: "Choisissez le prochain nœud exécutable dans Task Flow.",
    estimated: "Estimé",
  },
};

function tokenValue(node: TopologyState["nodes"][number]) {
  const value = node.payload.token_used ?? node.payload.tokens;
  return typeof value === "number" ? value : 0;
}

function formatTokens(value: number) {
  return value >= 1000 ? `${(value / 1000).toFixed(value >= 10_000 ? 0 : 1)}k` : String(value);
}

export function TokenModePanel({ session, nextTask, lang, compact = false }: TokenModePanelProps) {
  const copy = COPY[lang];
  const trace = session?.nodes.find((node) => node.payload.conductor_trace)?.payload.conductor_trace;
  const tokenBudget = trace?.budget.token_budget ?? null;
  const usedTokens = session?.stats.total_tokens ?? 0;
  const contextRatio = tokenBudget && tokenBudget > 0 ? Math.min(100, (usedTokens / tokenBudget) * 100) : 0;
  const contributors = [...(session?.nodes ?? [])]
    .map((node) => ({ node, tokens: tokenValue(node) }))
    .filter((item) => item.tokens > 0)
    .sort((left, right) => right.tokens - left.tokens)
    .slice(0, 3);
  const changedFiles = trace?.impact_summary?.changed_file_count ?? 0;
  const evidenceRefs = trace?.evidence_refs?.length ?? 0;
  const historyMessages = session?.nodes.length ?? 0;
  const handoffRecommended = historyMessages >= 8 || changedFiles >= 5 || evidenceRefs >= 5 || contextRatio >= 80;
  const action = session?.stats.errors
    ? "Review the failing topology node before adding more context."
    : nextTask?.description ?? copy.noAction;
  const verificationProfile = trace?.verification_strategy.kind || "focused";
  const mode = trace?.execution_mode || "token_efficient";

  return (
    <Surface as="section" elevated className={`token-mode-panel ${compact ? "token-mode-panel-compact" : ""} p-4 sm:p-5`} data-testid="token-mode-panel">
      <div className={`flex flex-col gap-4 ${compact ? "" : "xl:flex-row xl:items-start xl:justify-between"}`}>
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] accent-text">{copy.eyebrow}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold t1">{copy.title}</h2>
            <StatusBadge tone="accent">{mode}</StatusBadge>
          </div>
          <p className="mt-2 max-w-2xl text-xs leading-relaxed t2">
            {copy.context}: {copy.estimated} {formatTokens(usedTokens)}{tokenBudget ? ` / ${formatTokens(tokenBudget)}` : ""} tokens.
          </p>
        </div>
        <StatusBadge className="self-start whitespace-nowrap" tone={handoffRecommended ? "warning" : "success"}>
          {handoffRecommended ? copy.handoffRecommended : copy.handoffClear}
        </StatusBadge>
      </div>

      <div className={`mt-4 grid gap-3 ${compact ? "" : "lg:grid-cols-[minmax(0,1.1fr)_minmax(260px,0.9fr)]"}`}>
        <div>
          <div className="grid grid-cols-3 gap-2">
            <MetricTile label={copy.context} value={formatTokens(usedTokens)} tone="accent" />
            <MetricTile label={copy.profile} value={verificationProfile} />
            <MetricTile label={copy.handoff} value={handoffRecommended ? "Review" : "Clear"} tone={handoffRecommended ? "warning" : "success"} />
          </div>
          {tokenBudget && tokenBudget > 0 ? <ProgressBar ariaLabel={copy.context} className="mt-3" value={contextRatio} tone={handoffRecommended ? "warning" : "accent"} /> : null}
          <div className="mt-3 rounded-lg border px-3 py-2" style={{ borderColor: "var(--border-c)" }}>
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.nextAction}</p>
            <p className="mt-1 line-clamp-2 text-xs leading-relaxed t1" aria-label={action} title={action}>{action}</p>
          </div>
        </div>

        <div className="rounded-lg border px-3 py-2" style={{ borderColor: "var(--border-c)" }}>
          <p className="text-[10px] font-bold uppercase tracking-[0.12em] t3">{copy.contributors}</p>
          {contributors.length === 0 ? (
            <p className="mt-3 text-xs t2">{copy.noContributors}</p>
          ) : (
            <ol className="mt-2 space-y-2">
              {contributors.map(({ node, tokens }) => (
                <li key={node.id} className="flex items-center justify-between gap-3 text-xs">
                  <span className="min-w-0 truncate t1" title={node.title}>{node.title || node.node_type}</span>
                  <span className="flex-shrink-0 font-mono text-[10px] t3">{formatTokens(tokens)} tok</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </Surface>
  );
}
