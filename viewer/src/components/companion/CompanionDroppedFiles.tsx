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
      className="rounded-xl border border-cyan-500/20 bg-cyan-500/5 p-2.5 space-y-2 text-[11px]"
    >
      <div className="flex items-center justify-between text-[var(--t2)]">
        <span className="text-cyan-400 font-semibold flex items-center gap-1">
          <Folder className="h-3 w-3 text-cyan-400" />
          <span>情境檔案 ({droppedFiles.length})</span>
        </span>
        <button
          type="button"
          onClick={onClear}
          aria-label="Clear dropped files"
          className="text-[10px] text-[var(--t3)] hover:text-[var(--t1)] transition-colors"
        >
          清除
        </button>
      </div>

      <div className="max-h-16 overflow-y-auto space-y-0.5">
        {droppedFiles.map((file) => (
          <div
            key={`${file.name}-${file.lastModified}-${file.size}`}
            className="flex items-center gap-1.5 text-[var(--t2)] font-mono text-[10px]"
          >
            <Bot className="h-3 w-3 text-cyan-400 shrink-0" />
            <span className="truncate">{file.name}</span>
            <span className="text-[var(--t3)] text-[9px]">({(file.size / 1024).toFixed(1)} KB)</span>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-1.5 pt-1 border-t border-[var(--border-c)]">
        <input
          type="text"
          aria-label="Requirement description"
          value={quickPrompt}
          onChange={(e) => setQuickPrompt(e.target.value)}
          placeholder="需求描述 (例: 修復拖放檔案中的 bug)..."
          className="flex-1 bg-[var(--bg-muted)] border border-[var(--border-c)] rounded px-2 py-1 text-[10px] text-[var(--t1)] font-mono focus:outline-none focus:border-[var(--accent)]"
        />
        <button
          type="button"
          onClick={handleLaunch}
          disabled={launchingTask}
          aria-label="Launch task from dropped files"
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[var(--accent)] text-white font-bold text-[10px] transition-opacity hover:opacity-90 disabled:opacity-50 shrink-0"
        >
          <Play className="h-3 w-3" />
          <span>{launchingTask ? "建立中..." : "啟動任務"}</span>
        </button>
      </div>
    </div>
  );
}
