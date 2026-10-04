import { LinkButton, Card, CardContent, StatusBadge } from "../ui/primitives";
import { Database, FileText, Share2, ShieldCheck, ArrowRight } from "../ui/icons";

export function KnowledgePage() {
  return (
    <div className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto p-4 md:p-6" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4" style={{ borderColor: "var(--border-c)" }}>
        <div>
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-[var(--accent)]" />
            <h1 className="text-lg font-semibold tracking-tight text-[var(--t1)]">
              專案架構知識庫
            </h1>
            <StatusBadge tone="neutral">Obsidian 拓撲</StatusBadge>
          </div>
          <p className="mt-1 text-xs text-[var(--t3)] leading-relaxed">
            持久化知識拓撲、Obsidian 雙向鏈結與架構決策記錄 (ADR) 之可信存儲空間。
          </p>
        </div>
        <LinkButton to="/missions" variant="quiet" size="sm" className="inline-flex items-center gap-1.5 self-start md:self-auto">
          <span>前往任務清單</span>
          <ArrowRight className="h-3 w-3" />
        </LinkButton>
      </div>

      {/* 3-Tier Cognitive Relay Cards */}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="nordic-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--t1)]">
              <FileText className="h-3.5 w-3.5 text-zinc-400" />
              <span>Tier 1: stage.md</span>
            </div>
            <p className="mt-2 text-xs text-[var(--t3)] leading-relaxed">
              即時思考便簽與在途草稿，受 .gitignore 嚴格保護，絕不提交至版本庫。
            </p>
          </CardContent>
        </Card>

        <Card className="nordic-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--t1)]">
              <Share2 className="h-3.5 w-3.5 text-blue-400" />
              <span>Tier 2: handoff.md</span>
            </div>
            <p className="mt-2 text-xs text-[var(--t3)] leading-relaxed">
              跨代理人接棒中繼站，僅於自動化測試 100% 通過時記錄已驗證客觀事實。
            </p>
          </CardContent>
        </Card>

        <Card className="nordic-card">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-[var(--t1)]">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span>Tier 3: Obsidian Vault</span>
            </div>
            <p className="mt-2 text-xs text-[var(--t3)] leading-relaxed">
              docs/obsidian/ 模組知識拓撲，PR 合併時自動生成 3 行精簡英文註記。
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Connection Status Card */}
      <Card className="nordic-card mt-2">
        <CardContent className="flex flex-col items-center justify-center p-8 sm:p-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)] text-[var(--t2)]">
            <Database className="h-6 w-6" />
          </div>
          <h2 className="mt-4 text-base font-semibold text-[var(--t1)]">
            本機知識庫已就緒
          </h2>
          <p className="mx-auto mt-2 max-w-lg text-xs leading-relaxed text-[var(--t3)]">
            當前契約支援任務歷史、驗證證據與審計收據之雙向同步。依據 Rule 0.1 核心原則，嚴禁虛構或模擬未經測試驗證的知識記錄。
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <LinkButton to="/missions" variant="primary" size="sm">
              查看任務清單
            </LinkButton>
            <LinkButton to="/system" variant="quiet" size="sm">
              系統健康診斷
            </LinkButton>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
