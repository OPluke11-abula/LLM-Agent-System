import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  FileCode,
  Key,
  Lock,
  Radio,
  Sparkles,
  Unlock,
  X,
} from "../ui/icons";
import { useAmbientCompanion } from "../../hooks/useAmbientCompanion";

interface AmbientCompanionProps {
  standalone?: boolean;
  onClose?: () => void;
}

export function AmbientCompanion({ standalone = false, onClose }: AmbientCompanionProps) {
  const {
    status,
    connectionStatus,
    activeTask,
    approvalToken,
    setApprovalToken,
    actionMessage,
    errorMessage,
    droppedFiles,
    approve,
    deny,
    handleFileDrop,
    clearDroppedFiles,
  } = useAmbientCompanion();

  const [expanded, setExpanded] = useState<boolean>(true);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const onDragOverHandler = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const onDragLeaveHandler = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const onDropHandler = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileDrop(e.dataTransfer.files);
    }
  };

  const handle1ClickApprove = async () => {
    setSubmitting(true);
    await approve();
    setSubmitting(false);
  };

  const handle1ClickDeny = async () => {
    setSubmitting(true);
    await deny("Rejected from Ambient Companion");
    setSubmitting(false);
  };

  return (
    <div
      data-testid="ambient-companion-container"
      data-tauri-drag-region={standalone ? "true" : undefined}
      className={`font-sans select-none transition-all duration-300 ${
        standalone
          ? "w-full h-full p-2 bg-transparent flex flex-col justify-center"
          : "fixed bottom-5 right-5 z-50 max-w-sm w-full"
      }`}
      onDragOver={onDragOverHandler}
      onDragLeave={onDragLeaveHandler}
      onDrop={onDropHandler}
    >
      <div
        className={`relative overflow-hidden rounded-2xl border transition-all duration-300 shadow-2xl backdrop-blur-xl ${
          isDragOver
            ? "border-cyan-400 bg-cyan-950/80 shadow-[0_0_30px_rgba(34,211,238,0.4)]"
            : status === "awaiting_approval"
            ? "border-amber-500/60 bg-slate-950/90 shadow-[0_0_28px_rgba(245,158,11,0.25)]"
            : status === "verified"
            ? "border-emerald-500/50 bg-slate-950/90 shadow-[0_0_24px_rgba(16,185,129,0.25)]"
            : status === "thinking"
            ? "border-indigo-500/50 bg-slate-950/90 shadow-[0_0_20px_rgba(99,102,241,0.2)]"
            : "border-slate-800/80 bg-slate-950/85 text-slate-200"
        }`}
      >
        {/* Header telemetry pill */}
        <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-white/5 bg-white/[0.02]">
          <div className="flex items-center gap-2">
            {/* Status indicator with micro-animation */}
            <div className="relative flex items-center justify-center">
              {status === "idle" && (
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-40"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
                </span>
              )}

              {status === "thinking" && (
                <div className="flex items-center text-amber-400 animate-spin">
                  <Activity className="h-3.5 w-3.5" />
                </div>
              )}

              {status === "awaiting_approval" && (
                <div className="flex items-center text-amber-400 animate-bounce">
                  <Lock className="h-3.5 w-3.5" />
                </div>
              )}

              {status === "verified" && (
                <div className="flex items-center text-emerald-400 transform scale-110 transition-transform">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
              )}

              {status === "error" && (
                <div className="flex items-center text-rose-400">
                  <AlertTriangle className="h-3.5 w-3.5" />
                </div>
              )}
            </div>

            <span className="text-xs font-semibold tracking-wide text-slate-100 flex items-center gap-1.5">
              <span>LAS Companion</span>
              {connectionStatus === "connected" ? (
                <Radio className="h-2.5 w-2.5 text-emerald-400 inline" />
              ) : (
                <span className="text-[10px] text-slate-500 font-mono">({connectionStatus})</span>
              )}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setExpanded(!expanded)}
              aria-label="Toggle details"
              className="text-slate-400 hover:text-slate-200 p-1 rounded-md text-[10px] font-mono hover:bg-white/5 transition-colors"
            >
              {expanded ? "COLLAPSE" : "EXPAND"}
            </button>

            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close companion"
                className="text-slate-400 hover:text-rose-400 p-1 rounded-md transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Dynamic Body content */}
        {expanded && (
          <div className="p-3.5 space-y-3">
            {/* Action or telemetry text */}
            {actionMessage && (
              <p
                data-testid="companion-action-message"
                className="text-[11px] leading-relaxed text-slate-300 font-mono line-clamp-2 bg-black/40 px-2.5 py-1.5 rounded-lg border border-white/5"
              >
                {actionMessage}
              </p>
            )}

            {/* Error Message */}
            {errorMessage && (
              <div
                data-testid="companion-error-message"
                className="text-[11px] text-rose-300 bg-rose-950/40 border border-rose-800/50 p-2 rounded-lg flex items-start gap-2"
              >
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-rose-400 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* 1-Click HITL Approval Card */}
            {status === "awaiting_approval" && activeTask && (
              <div
                data-testid="companion-hitl-card"
                className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-3 space-y-2.5 transition-all shadow-inner"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold font-mono tracking-wider text-amber-300 uppercase px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-500/30">
                    HITL Approval Required
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">{activeTask.taskId}</span>
                </div>

                <div className="space-y-1 text-xs">
                  <p className="text-slate-200 font-medium text-[11px] line-clamp-2">
                    {activeTask.planSummary || "Stop-and-Wait Architecture Gate awaiting sign-off."}
                  </p>
                  {activeTask.targetFiles && activeTask.targetFiles.length > 0 && (
                    <div className="flex items-center gap-1 text-[10px] font-mono text-amber-200/90 truncate">
                      <FileCode className="h-3 w-3 shrink-0 text-amber-400" />
                      <span>{activeTask.targetFiles.join(", ")}</span>
                    </div>
                  )}
                </div>

                {/* Token input field with fallback */}
                <div className="flex items-center gap-1.5 pt-1">
                  <Key className="h-3 w-3 text-amber-400 shrink-0" />
                  <input
                    type="password"
                    aria-label="HITL Approval Token"
                    value={approvalToken}
                    onChange={(e) => setApprovalToken(e.target.value)}
                    placeholder="Enter approval token..."
                    className="w-full bg-black/60 border border-white/10 rounded px-2 py-1 text-[11px] text-white font-mono focus:outline-none focus:border-amber-400"
                  />
                </div>

                {/* 1-Click Action Buttons */}
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={handle1ClickApprove}
                    disabled={submitting}
                    aria-label="Allow and execute"
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-950/50 transition-all disabled:opacity-50"
                  >
                    <Unlock className="h-3.5 w-3.5" />
                    <span>{submitting ? "Approving..." : "Allow (PO Luke)"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handle1ClickDeny}
                    disabled={submitting}
                    aria-label="Deny mutation"
                    className="inline-flex items-center justify-center px-3 py-1.5 rounded-lg bg-rose-950/60 hover:bg-rose-900 border border-rose-800/60 text-rose-300 font-medium text-xs transition-colors disabled:opacity-50"
                  >
                    <span>Deny</span>
                  </button>
                </div>
              </div>
            )}

            {/* Verified green leap banner */}
            {status === "verified" && (
              <div
                data-testid="companion-verified-badge"
                className="flex items-center gap-2.5 p-2.5 rounded-xl border border-emerald-500/30 bg-emerald-950/30 text-emerald-200"
              >
                <div className="p-1 rounded-full bg-emerald-500/20 text-emerald-400">
                  <Sparkles className="h-4 w-4" />
                </div>
                <div className="text-xs">
                  <div className="font-bold text-emerald-300">Verification Gate Passed</div>
                  <div className="text-[10px] text-emerald-400/80">Merkle root secured & ready to export.</div>
                </div>
              </div>
            )}

            {/* Dropped files context list */}
            {droppedFiles.length > 0 && (
              <div className="rounded-lg border border-white/10 bg-black/30 p-2 space-y-1 text-[11px]">
                <div className="flex items-center justify-between text-slate-400">
                  <span>Context Files ({droppedFiles.length})</span>
                  <button
                    type="button"
                    onClick={clearDroppedFiles}
                    className="text-[10px] text-slate-500 hover:text-slate-300"
                  >
                    Clear
                  </button>
                </div>
                <div className="max-h-16 overflow-y-auto space-y-0.5">
                  {droppedFiles.map((file, idx) => (
                    <div key={`${file.name}-${idx}`} className="flex items-center gap-1.5 text-slate-300 font-mono text-[10px]">
                      <Bot className="h-3 w-3 text-cyan-400 shrink-0" />
                      <span className="truncate">{file.name}</span>
                      <span className="text-slate-500 text-[9px]">({(file.size / 1024).toFixed(1)} KB)</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Drag & Drop Context ingestion target hint */}
            <div
              className={`border border-dashed rounded-lg p-2 text-center text-[10px] font-mono transition-colors ${
                isDragOver
                  ? "border-cyan-400 bg-cyan-900/30 text-cyan-200"
                  : "border-slate-800 text-slate-500 hover:border-slate-700"
              }`}
            >
              {isDragOver ? "Drop files to inject context" : "Drag files here to add context"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
