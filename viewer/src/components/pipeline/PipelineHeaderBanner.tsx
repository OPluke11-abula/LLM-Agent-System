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
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
      <div>
        <div className="flex items-center gap-2.5">
          <Workflow className="h-6 w-6 text-indigo-400" />
          <h1 className="text-xl font-bold tracking-tight t1">
            {lang === "zh" ? "自主編程流水線" : "Autonomous Coding Pipeline"}
          </h1>
          <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-mono text-indigo-300">
            Protocol v3.8.0 | ADR-006
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Requirement Intake → Bounded Worktree Mutation → Live Verification Ladder → Cryptographic Draft PR
        </p>
      </div>

      <div className="flex items-center gap-2">
        <span
          className={cx(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
            wsConnected
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
          )}
        >
          <span
            className={cx(
              "h-2 w-2 rounded-full",
              wsConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
            )}
          />
          {wsConnected ? "Telemetry Live" : "Offline"}
        </span>

        <Button variant="outline" size="sm" onClick={onSync}>
          <RefreshCw className="h-3.5 w-3.5 mr-1" />
          Sync
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={onOpenBenchmark}
          className="border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/10"
        >
          <Activity className="h-3.5 w-3.5 mr-1 text-indigo-400" />
          {lang === "zh" ? "黃金基準測試 (P4)" : "Golden Benchmark (P4)"}
        </Button>

        <Button
          variant="primary"
          size="sm"
          onClick={onOpenCreateModal}
          className="bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_12px_rgba(99,102,241,0.4)]"
        >
          <Play className="h-3.5 w-3.5 mr-1" />
          New Coding Task
        </Button>
      </div>
    </div>
  );
};
