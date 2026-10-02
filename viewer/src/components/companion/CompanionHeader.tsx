import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Radio,
  X,
} from "../ui/icons";
import type { CompanionStatus, CompanionConnectionStatus } from "../../hooks/useAmbientCompanion";

interface CompanionHeaderProps {
  status: CompanionStatus;
  connectionStatus: CompanionConnectionStatus;
  expanded: boolean;
  onToggleExpand: () => void;
  onClose?: () => void;
}

export function CompanionHeader({
  status,
  connectionStatus,
  expanded,
  onToggleExpand,
  onClose,
}: CompanionHeaderProps) {
  return (
    <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-white/5 bg-white/[0.02]">
      <div className="flex items-center gap-2">
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
          onClick={onToggleExpand}
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
  );
}
