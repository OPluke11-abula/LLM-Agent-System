import React from "react";
import { Button } from "../ui/primitives";
import { cx } from "../ui/utils";
import { Activity, Play, RefreshCw, Workflow } from "../ui/icons";

interface PipelineHeaderBannerProps {
  lang?: string;
  wsConnected: boolean;
  onSync: () => void;
  onOpenBenchmark: () => void;
  onOpenCreateModal: () => void;
}

export const PipelineHeaderBanner: React.FC<PipelineHeaderBannerProps> = ({
  lang = "zh",
  wsConnected,
  onSync,
  onOpenBenchmark,
  onOpenCreateModal,
}) => {
  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between border-b border-[var(--border-c)] pb-3.5">
      <div>
        <div className="flex items-center gap-2">
          <Workflow className="h-4 w-4 text-blue-400" />
          <h1 className="text-base font-semibold tracking-tight t1">
            {lang === "zh" ? "自主編程流水線" : "Autonomous Coding Pipeline"}
          </h1>
          <span className="rounded-md border border-[var(--border-c)] bg-[var(--bg-muted)] px-2 py-0.5 text-[11px] font-mono text-[var(--t2)]">
            PAP v3.8.0
          </span>
        </div>
        <p className="mt-1 text-xs text-[var(--t3)]">
          {lang === "zh"
            ? "需求解析 → 隔離工作樹變更 → 多階驗證天梯 → 密碼學 Draft PR 產出"
            : "Requirement Intake → Bounded Worktree Mutation → Live Verification Ladder → Cryptographic Draft PR"}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cx(
            "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-mono",
            wsConnected
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
          )}
        >
          <span
            className={cx(
              "h-1.5 w-1.5 rounded-full",
              wsConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
            )}
          />
          {wsConnected
            ? (lang === "zh" ? "即時遙測" : "Live")
            : (lang === "zh" ? "離線" : "Offline")}
        </span>

        <Button variant="outline" size="sm" onClick={onSync}>
          <RefreshCw className="h-3.5 w-3.5 mr-1 text-[var(--t3)]" />
          {lang === "zh" ? "同步" : "Sync"}
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={onOpenBenchmark}
        >
          <Activity className="h-3.5 w-3.5 mr-1 text-blue-400" />
          {lang === "zh" ? "基準測試" : "Benchmark"}
        </Button>

        <Button
          variant="primary"
          size="sm"
          onClick={onOpenCreateModal}
        >
          <Play className="h-3.5 w-3.5 mr-1" />
          {lang === "zh" ? "建立編程任務" : "New Coding Task"}
        </Button>
      </div>
    </div>
  );
};
