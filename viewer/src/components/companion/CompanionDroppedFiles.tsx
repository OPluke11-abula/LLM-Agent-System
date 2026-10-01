import { useState } from "react";
import { Bot, Folder, Play } from "../ui/icons";
import type { DroppedFileItem } from "../../hooks/useAmbientCompanion";

interface CompanionDroppedFilesProps {
  droppedFiles: DroppedFileItem[];
  onClear: () => void;
  onLaunch: (prompt?: string) => Promise<unknown>;
}

export function CompanionDroppedFiles({
  droppedFiles,
  onClear,
  onLaunch,
}: CompanionDroppedFilesProps) {
  const [quickPrompt, setQuickPrompt] = useState<string>("");
  const [launchingTask, setLaunchingTask] = useState<boolean>(false);

  const handleLaunch = async () => {
    setLaunchingTask(true);
    await onLaunch(quickPrompt);
    setQuickPrompt("");
    setLaunchingTask(false);
  };

  if (droppedFiles.length === 0) return null;

  return (
    <div
      data-testid="companion-dropped-files-card"
      className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-2.5 space-y-2 text-[11px]"
    >
      <div className="flex items-center justify-between text-slate-400">
        <span className="text-cyan-300 font-semibold flex items-center gap-1">
          <Folder className="h-3 w-3 text-cyan-400" />
          <span>Context Files ({droppedFiles.length})</span>
        </span>
        <button
          type="button"
          onClick={onClear}
          aria-label="Clear dropped files"
          className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          Clear
        </button>
      </div>

      <div className="max-h-16 overflow-y-auto space-y-0.5">
        {droppedFiles.map((file) => (
          <div
            key={`${file.name}-${file.lastModified}-${file.size}`}
            className="flex items-center gap-1.5 text-slate-300 font-mono text-[10px]"
          >
            <Bot className="h-3 w-3 text-cyan-400 shrink-0" />
            <span className="truncate">{file.name}</span>
            <span className="text-slate-500 text-[9px]">({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-1.5 pt-1 border-t border-cyan-500/10">
        <input
          type="text"
          aria-label="Requirement description"
          value={quickPrompt}
          onChange={(e) => setQuickPrompt(e.target.value)}
          placeholder="Requirement (e.g. fix bug in dropped file)..."
          className="flex-1 bg-black/60 border border-white/10 rounded px-2 py-1 text-[10px] text-white font-mono focus:outline-none focus:border-cyan-400"
        />
        <button
          type="button"
          onClick={handleLaunch}
          disabled={launchingTask}
          aria-label="Launch task from dropped files"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-[10px] transition-colors disabled:opacity-50 shrink-0"
        >
          <Play className="h-3 w-3" />
          <span>{launchingTask ? "Starting..." : "Launch"}</span>
        </button>
      </div>
    </div>
  );
}
