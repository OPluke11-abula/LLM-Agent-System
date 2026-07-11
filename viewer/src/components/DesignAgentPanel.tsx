import { StatusBadge, Surface } from "./ui/primitives";
import type { Lang, TopologyState } from "../types";

type DesignAgentPanelProps = {
  readonly session: TopologyState | null;
  readonly lang: Lang;
};

type DesignAgentCopy = {
  readonly title: string;
  readonly eyebrow: string;
  readonly approved: string;
  readonly direction: string;
  readonly packet: string;
  readonly findings: string;
  readonly evidence: string;
  readonly debt: string;
  readonly nextTask: string;
  readonly evidencePending: string;
  readonly noNextTask: string;
};

const DESIGN_STATE = {
  direction: "Cognitive Operations Atlas",
  personality: "Refined Technical Cartography",
  packet: ".agent/knowledge_base/exports/phase-71-las-viewer-art-direction-packet-2026-07-07.md",
} as const;

const COPY: Record<Lang, DesignAgentCopy> = {
  zh: {
    title: "Design Agent",
    eyebrow: "DESIGN OPERATING STATE",
    approved: "設計包已核准",
    direction: "目前藝術方向",
    packet: "已核准設計包",
    findings: "開放設計發現",
    evidence: "截圖證據",
    debt: "未解決品味債務",
    nextTask: "下一個設計優先任務",
    evidencePending: "等待目前版本的桌面與行動版截圖",
    noNextTask: "下一個 Viewer 變更先執行獨立設計審查。",
  },
  en: {
    title: "Design Agent",
    eyebrow: "DESIGN OPERATING STATE",
    approved: "Packet approved",
    direction: "Current art direction",
    packet: "Approved design packet",
    findings: "Open design findings",
    evidence: "Screenshot evidence",
    debt: "Unresolved taste debt",
    nextTask: "Next design-first task",
    evidencePending: "Current-build desktop and mobile captures pending",
    noNextTask: "Run independent design review before the next viewer slice.",
  },
  ja: {
    title: "Design Agent",
    eyebrow: "DESIGN OPERATING STATE",
    approved: "デザインパケット承認済み",
    direction: "現在のアート方向",
    packet: "承認済みデザインパケット",
    findings: "未解決のデザイン指摘",
    evidence: "スクリーンショット証拠",
    debt: "未解決のテイスト負債",
    nextTask: "次のデザイン優先タスク",
    evidencePending: "現行ビルドのデスクトップとモバイル画像を待機中",
    noNextTask: "次の Viewer 変更前に独立デザインレビューを実行します。",
  },
  fr: {
    title: "Design Agent",
    eyebrow: "DESIGN OPERATING STATE",
    approved: "Dossier approuvé",
    direction: "Direction artistique actuelle",
    packet: "Dossier de design approuvé",
    findings: "Constats design ouverts",
    evidence: "Preuves par capture",
    debt: "Dette de goût non résolue",
    nextTask: "Prochaine tâche design prioritaire",
    evidencePending: "Captures desktop et mobile du build actuel en attente",
    noNextTask: "Lancer une revue design indépendante avant la prochaine évolution du viewer.",
  },
};

function collectDesignSignals(session: TopologyState | null) {
  const designNodes = (session?.nodes ?? []).filter((node) => {
    const text = `${node.id} ${node.title} ${node.description}`.toLowerCase();
    return ["design", "visual", "typography", "spacing", "motion", "vibe", "taste"].some((term) => text.includes(term));
  });
  const openNodes = designNodes.filter((node) => node.status !== "completed" && node.status !== "done");
  const findings = openNodes.filter((node) => /design[-_ ]|finding/.test(`${node.id} ${node.title}`.toLowerCase()));
  const tasteDebt = openNodes.filter((node) => /taste|vibe|polish|typography|spacing|motion|visual/.test(`${node.title} ${node.description}`.toLowerCase()));
  const evidence = [...new Set(
    (session?.nodes ?? [])
      .flatMap((node) => node.payload.conductor_trace?.evidence_refs ?? [])
      .filter((ref) => /viewer[\\/]output|\.(png|jpe?g|webp)$/i.test(ref)),
  )];

  return {
    findings,
    tasteDebt,
    evidence,
    nextDesignTask: openNodes[0]?.description || openNodes[0]?.title,
  };
}

export function DesignAgentPanel({ session, lang }: DesignAgentPanelProps) {
  const copy = COPY[lang];
  const signals = collectDesignSignals(session);
  const evidenceLabel = signals.evidence[0] ?? copy.evidencePending;
  const nextDesignTask = signals.nextDesignTask ?? copy.noNextTask;

  return (
    <Surface as="section" elevated className="overflow-hidden" data-testid="design-agent-panel">
      <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] accent-text">{copy.eyebrow}</p>
          <h2 className="mt-1 text-lg font-semibold t1">{copy.title}</h2>
        </div>
        <StatusBadge className="self-start whitespace-nowrap" tone="success">{copy.approved}</StatusBadge>
      </div>

      <div className="border-t" style={{ borderColor: "var(--border-c)" }}>
        <div className="grid min-w-0 sm:grid-cols-[minmax(0,1.2fr)_minmax(12rem,0.8fr)]">
          <div className="min-w-0 px-4 py-3 sm:border-r" style={{ borderColor: "var(--border-c)" }}>
            <p className="text-[10px] font-semibold uppercase tracking-[0.1em] t3">{copy.direction}</p>
            <p className="mt-1 text-sm font-semibold t1">{DESIGN_STATE.direction}</p>
            <p className="mt-1 text-xs t2">{DESIGN_STATE.personality}</p>
            <p className="mt-3 text-[10px] font-semibold uppercase tracking-[0.1em] t3">{copy.packet}</p>
            <p className="mt-1 break-all font-mono text-[10px] leading-relaxed t2">{DESIGN_STATE.packet}</p>
          </div>

          <dl className="grid min-w-0 grid-cols-1 border-t sm:border-t-0" style={{ borderColor: "var(--border-c)" }}>
            <div className="flex items-center justify-between gap-3 px-3 py-2.5">
              <dt className="text-[10px] font-semibold uppercase tracking-[0.08em] t3">{copy.findings}</dt>
              <dd className="text-sm font-semibold t1" data-testid="design-findings-count">{session ? signals.findings.length : "N/A"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 border-t px-3 py-2.5" style={{ borderColor: "var(--border-c)" }}>
              <dt className="text-[10px] font-semibold uppercase tracking-[0.08em] t3">{copy.evidence}</dt>
              <dd className="text-sm font-semibold t1" data-testid="design-evidence-count">{session ? signals.evidence.length : "N/A"}</dd>
            </div>
            <div className="flex items-center justify-between gap-3 border-t px-3 py-2.5" style={{ borderColor: "var(--border-c)" }}>
              <dt className="text-[10px] font-semibold uppercase tracking-[0.08em] t3">{copy.debt}</dt>
              <dd className="text-sm font-semibold t1" data-testid="design-debt-count">{session ? signals.tasteDebt.length : "N/A"}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="grid min-w-0 border-t sm:grid-cols-2" style={{ borderColor: "var(--border-c)" }}>
        <div className="min-w-0 px-4 py-3 sm:border-r" style={{ borderColor: "var(--border-c)" }}>
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] t3">{copy.evidence}</p>
          <p className="mt-1 break-all text-xs leading-relaxed t2" data-testid="design-evidence-ref">{evidenceLabel}</p>
        </div>
        <div className="min-w-0 border-t px-4 py-3 sm:border-t-0" style={{ borderColor: "var(--border-c)" }}>
          <p className="text-[10px] font-semibold uppercase tracking-[0.1em] t3">{copy.nextTask}</p>
          <p className="mt-1 break-words text-xs leading-relaxed t1" data-testid="design-next-task">{nextDesignTask}</p>
        </div>
      </div>
    </Surface>
  );
}
