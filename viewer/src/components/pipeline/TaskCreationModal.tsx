
import { Button } from "../ui/primitives";
import { Workflow, Users } from "../ui/icons";

interface TaskCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
  newTaskId: string;
  setNewTaskId: (v: string) => void;
  newRepoPath: string;
  setNewRepoPath: (v: string) => void;
  newRequirement: string;
  setNewRequirement: (v: string) => void;
  newTargetBranch: string;
  setNewTargetBranch: (v: string) => void;
  newRole: string;
  setNewRole: (v: string) => void;
  newInspectedFiles: string;
  setNewInspectedFiles: (v: string) => void;
  newTargetFiles: string;
  setNewTargetFiles: (v: string) => void;
  enableCommittee: boolean;
  setEnableCommittee: (v: boolean) => void;
  debateRounds: number;
  setDebateRounds: (v: number) => void;
  offlineMode: boolean;
  setOfflineMode: (v: boolean) => void;
  thinkingBudget: number;
  setThinkingBudget: (v: number) => void;
  useMesh: boolean;
  setUseMesh: (v: boolean) => void;
  loading: boolean;
  onSubmit: () => void;
}

export function TaskCreationModal({
  isOpen,
  onClose,
  newTaskId,
  setNewTaskId,
  newRepoPath,
  setNewRepoPath,
  newRequirement,
  setNewRequirement,
  newTargetBranch,
  setNewTargetBranch,
  newRole,
  setNewRole,
  newInspectedFiles,
  setNewInspectedFiles,
  newTargetFiles,
  setNewTargetFiles,
  enableCommittee,
  setEnableCommittee,
  debateRounds,
  setDebateRounds,
  offlineMode,
  setOfflineMode,
  thinkingBudget,
  setThinkingBudget,
  useMesh,
  setUseMesh,
  loading,
  onSubmit,
}: TaskCreationModalProps) {
  if (!isOpen) return null;

  const handleBudgetChange = (val: string) => {
    const parsed = parseInt(val, 10);
    setThinkingBudget(Number.isFinite(parsed) && !Number.isNaN(parsed) ? parsed : 0);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-[var(--bg-card)] border border-[var(--border-c)] rounded-xl max-w-lg w-full p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-[var(--border-c)] pb-3">
          <h3 className="text-sm font-semibold text-[var(--t1)] flex items-center gap-2">
            <Workflow className="h-4 w-4 text-[var(--accent)]" />
            初始化自主編程任務 (Initialize Coding Task)
          </h3>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="text-[var(--t3)] hover:text-[var(--t1)] text-xs"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <div>
            <label htmlFor="init-task-id" className="block text-[var(--t2)] font-mono mb-1">任務識別碼 (Task ID)</label>
            <input
              id="init-task-id"
              type="text"
              aria-label="Task ID"
              value={newTaskId}
              onChange={(e) => setNewTaskId(e.target.value)}
              className="w-full bg-[var(--bg-muted)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-[var(--t1)] font-mono text-xs focus:border-[var(--border-strong)] focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="init-repo-path" className="block text-[var(--t2)] font-mono mb-1">目標儲存庫路徑 (Target Repository Path)</label>
            <input
              id="init-repo-path"
              type="text"
              aria-label="Target Repository Path"
              value={newRepoPath}
              onChange={(e) => setNewRepoPath(e.target.value)}
              placeholder="Absolute path to target repository..."
              className="w-full bg-[var(--bg-muted)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-[var(--t1)] font-mono text-xs focus:border-[var(--border-strong)] focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="init-requirement" className="block text-[var(--t2)] font-mono mb-1">需求提示詞 (Requirement Prompt)</label>
            <textarea
              id="init-requirement"
              rows={3}
              aria-label="Requirement Prompt"
              value={newRequirement}
              onChange={(e) => setNewRequirement(e.target.value)}
              placeholder="請輸入編程需求描述..."
              className="w-full bg-[var(--bg-muted)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-[var(--t1)] text-xs focus:border-[var(--border-strong)] focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="init-target-branch" className="block text-[var(--t2)] font-mono mb-1">目標分支 (Target Branch)</label>
              <input
                id="init-target-branch"
                type="text"
                aria-label="Target Branch"
                value={newTargetBranch}
                onChange={(e) => setNewTargetBranch(e.target.value)}
                className="w-full bg-[var(--bg-muted)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-[var(--t1)] font-mono text-xs focus:border-[var(--border-strong)] focus:outline-none"
              />
            </div>
            <div>
              <label htmlFor="init-specialist-role" className="block text-[var(--t2)] font-mono mb-1">專家角色 (Specialist Role)</label>
              <select
                id="init-specialist-role"
                aria-label="Specialist Role"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="w-full bg-[var(--bg-muted)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-[var(--t1)] font-mono text-xs focus:border-[var(--border-strong)] focus:outline-none"
              >
                <option value="DOMAIN_LOGIC_AGENT">DOMAIN_LOGIC_AGENT</option>
                <option value="BACKEND_INFRA_AGENT">BACKEND_INFRA_AGENT</option>
                <option value="UI_UX_AGENT">UI_UX_AGENT</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="init-inspected-files" className="block text-[var(--t2)] font-mono mb-1">
              調研檔案清單 (Anti-Summary Invariant)
            </label>
            <input
              id="init-inspected-files"
              type="text"
              aria-label="Inspected Files"
              value={newInspectedFiles}
              onChange={(e) => setNewInspectedFiles(e.target.value)}
              className="w-full bg-[var(--bg-muted)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-[var(--t1)] font-mono text-xs focus:border-[var(--border-strong)] focus:outline-none"
            />
          </div>

          <div>
            <label htmlFor="init-target-files" className="block text-[var(--t2)] font-mono mb-1">目標修改檔案 (Target Files to Modify)</label>
            <input
              id="init-target-files"
              type="text"
              aria-label="Target Files to Modify"
              value={newTargetFiles}
              onChange={(e) => setNewTargetFiles(e.target.value)}
              className="w-full bg-[var(--bg-muted)] border border-[var(--border-c)] rounded-md px-3 py-1.5 text-[var(--t1)] font-mono text-xs focus:border-[var(--border-strong)] focus:outline-none"
            />
          </div>

          {/* Committee Debate Controls */}
          <div className="rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableCommittee}
                  onChange={(e) => setEnableCommittee(e.target.checked)}
                  className="rounded border-[var(--border-strong)] bg-[var(--bg-card)] text-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <span className="text-[var(--t1)] font-semibold flex items-center gap-1.5">
                  <Users className="h-3.5 w-3.5 text-[var(--accent)]" />
                  啟用專家委員會辯論 (Phase 85)
                </span>
              </label>
              <span className="text-[10px] text-[var(--accent)] font-mono">共識閘門</span>
            </div>
            {enableCommittee && (
              <div className="flex items-center gap-2.5 pt-1 text-[11px] text-[var(--t2)]">
                <span className="text-[var(--t3)] font-mono">審議輪次:</span>
                <select
                  aria-label="Deliberation rounds"
                  value={debateRounds}
                  onChange={(e) => setDebateRounds(Number(e.target.value))}
                  className="bg-[var(--bg-card)] border border-[var(--border-c)] rounded px-2 py-1 text-[var(--t1)] font-mono text-xs"
                >
                  <option value={1}>1 輪 (快速審查)</option>
                  <option value={2}>2 輪 (深度質詢)</option>
                  <option value={3}>3 輪 (窮舉共識)</option>
                </select>
                <span className="text-[var(--t3)] text-[10px]">自動排程架構、資安與 QA</span>
              </div>
            )}
          </div>

          {/* Dynamic Reasoning & Offline Controls (Phase 86) */}
          <div className="rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={offlineMode}
                  onChange={(e) => setOfflineMode(e.target.checked)}
                  className="rounded border-[var(--border-strong)] bg-[var(--bg-card)] text-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <span className="text-[var(--t1)] font-semibold flex items-center gap-1.5">
                  🔒 實體隔離離線模式 (Phase 86)
                </span>
              </label>
              <span className="text-[10px] text-[var(--t3)] font-mono">Ollama 本地</span>
            </div>
            <div className="flex items-center justify-between gap-3 pt-1 text-[11px]">
              <span className="text-[var(--t3)] font-mono">思考配額 (Thinking Budget):</span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  aria-label="Thinking budget tokens"
                  value={thinkingBudget}
                  onChange={(e) => handleBudgetChange(e.target.value)}
                  step={1024}
                  min={0}
                  max={32768}
                  className="w-24 bg-[var(--bg-card)] border border-[var(--border-c)] rounded px-2 py-0.5 text-[var(--t1)] font-mono text-xs text-right"
                />
                <span className="text-[var(--t3)] font-mono text-[10px]">tokens</span>
              </div>
            </div>
          </div>

          {/* Federated P2P Mesh Controls (Phase 87) */}
          <div className="rounded-lg border border-[var(--border-c)] bg-[var(--bg-muted)] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useMesh}
                  onChange={(e) => setUseMesh(e.target.checked)}
                  className="rounded border-[var(--border-strong)] bg-[var(--bg-card)] text-[var(--accent)] focus:ring-[var(--accent)]"
                />
                <span className="text-[var(--t1)] font-semibold flex items-center gap-1.5">
                  🌐 聯邦 P2P 網格運算 (Phase 87)
                </span>
              </label>
              <span className="text-[10px] text-[var(--t3)] font-mono">工作樹叢集</span>
            </div>
            <p className="text-[10px] text-[var(--t3)]">
              將推理辯論與測試天梯卸載至去中心化節點執行
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border-c)]">
          <Button variant="outline" size="sm" onClick={onClose}>
            取消
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onSubmit}
            disabled={loading || !newRequirement}
          >
            提交並執行預檢 (Submit & Precheck)
          </Button>
        </div>
      </div>
    </div>
  );
}
