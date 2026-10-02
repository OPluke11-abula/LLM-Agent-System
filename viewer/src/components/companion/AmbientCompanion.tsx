import { useEffect, useState, type DragEvent } from "react";
import { AlertTriangle, Sparkles } from "../ui/icons";
import { useAmbientCompanion, type CompanionStatus } from "../../hooks/useAmbientCompanion";
import { CompanionHeader } from "./CompanionHeader";
import { CompanionStageTracker } from "./CompanionStageTracker";
import { CompanionHitlCard } from "./CompanionHitlCard";
import { CompanionDroppedFiles } from "./CompanionDroppedFiles";

interface AmbientCompanionProps {
  standalone?: boolean;
  onClose?: () => void;
}

function getCompanionBorderClasses(isDragOver: boolean, status: CompanionStatus): string {
  if (isDragOver) {
    return "border-cyan-400 bg-cyan-950/80 shadow-[0_0_30px_rgba(34,211,238,0.4)]";
  }
  switch (status) {
    case "awaiting_approval":
      return "border-amber-500/60 bg-slate-950/90 shadow-[0_0_28px_rgba(245,158,11,0.25)]";
    case "verified":
      return "border-emerald-500/50 bg-slate-950/90 shadow-[0_0_24px_rgba(16,185,129,0.25)]";
    case "thinking":
      return "border-indigo-500/50 bg-slate-950/90 shadow-[0_0_20px_rgba(99,102,241,0.2)]";
    default:
      return "border-slate-800/80 bg-slate-950/85 text-slate-200";
  }
}

function VerifiedBadge() {
  return (
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
  );
}

export function AmbientCompanion({ standalone = false, onClose }: AmbientCompanionProps) {
  const {
    status,
    connectionStatus,
    activeTask,
    currentStageIndex,
    totalStages,
    approvalToken,
    setApprovalToken,
    actionMessage,
    errorMessage,
    droppedFiles,
    approve,
    deny,
    createTaskFromDrop,
    handleFileDrop,
    clearDroppedFiles,
  } = useAmbientCompanion();

  const [expanded, setExpanded] = useState<boolean>(true);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.altKey && (e.key === "c" || e.key === "C")) {
        e.preventDefault();
        setExpanded((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const onDragOverHandler = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const onDragLeaveHandler = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const onDropHandler = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileDrop(e.dataTransfer.files);
    }
  };

  const handle1ClickApprove = async () => {
    setSubmitting(true);
    try {
      await approve();
    } finally {
      setSubmitting(false);
    }
  };

  const handle1ClickDeny = async () => {
    setSubmitting(true);
    try {
      await deny("Rejected from Ambient Companion");
    } finally {
      setSubmitting(false);
    }
  };

  const borderClass = getCompanionBorderClasses(isDragOver, status);

  return (
    <div
      data-testid="ambient-companion-container"
      data-tauri-drag-region={standalone ? "true" : undefined}
      className={`font-sans select-none transition-colors duration-300 ${
        standalone
          ? "w-full h-full p-2 bg-transparent flex flex-col justify-center"
          : "fixed bottom-5 right-5 z-50 max-w-sm w-full"
      }`}
      onDragOver={onDragOverHandler}
      onDragLeave={onDragLeaveHandler}
      onDrop={onDropHandler}
    >
      <div className={`relative overflow-hidden rounded-2xl border transition-colors duration-300 shadow-2xl backdrop-blur-xl ${borderClass}`}>
        <CompanionHeader
          status={status}
          connectionStatus={connectionStatus}
          expanded={expanded}
          onToggleExpand={() => setExpanded(!expanded)}
          onClose={onClose}
        />

        {expanded && (
          <div className="p-3.5 space-y-3">
            {actionMessage && (
              <p
                data-testid="companion-action-message"
                className="text-[11px] leading-relaxed text-slate-300 font-mono line-clamp-2 bg-black/40 px-2.5 py-1.5 rounded-lg border border-white/5"
              >
                {actionMessage}
              </p>
            )}

            {errorMessage && (
              <div
                data-testid="companion-error-message"
                className="text-[11px] text-rose-300 bg-rose-950/40 border border-rose-800/50 p-2 rounded-lg flex items-start gap-2"
              >
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-rose-400 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {activeTask?.stage && (
              <CompanionStageTracker
                stage={activeTask.stage}
                currentStageIndex={currentStageIndex}
                totalStages={totalStages}
                status={status}
              />
            )}

            {status === "awaiting_approval" && activeTask && (
              <CompanionHitlCard
                activeTask={activeTask}
                approvalToken={approvalToken}
                submitting={submitting}
                onTokenChange={setApprovalToken}
                onApprove={handle1ClickApprove}
                onDeny={handle1ClickDeny}
              />
            )}

            {status === "verified" && <VerifiedBadge />}

            <CompanionDroppedFiles
              droppedFiles={droppedFiles}
              onClear={clearDroppedFiles}
              onLaunch={createTaskFromDrop}
            />

            <div
              className={`border border-dashed rounded-lg p-2 text-center text-[10px] font-mono transition-colors ${
                isDragOver
                  ? "border-cyan-400 bg-cyan-900/30 text-cyan-200"
                  : "border-slate-800 text-slate-500 hover:border-slate-700"
              }`}
            >
              {isDragOver ? "Drop files to inject context" : "Drag files here to add context (Alt+C)"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
