
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="card-bg border border-border-c rounded-xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Workflow className="h-4 w-4 text-indigo-400" />
            Initialize Autonomous Coding Task
          </h3>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="text-slate-400 hover:text-white text-xs"
          >
            ✕
          </button>
        </div>

        <div className="space-y-3 text-xs">
          <div>
            <label htmlFor="init-task-id" className="block text-slate-400 font-mono mb-1">Task ID</label>
            <input
              id="init-task-id"
              type="text"
              aria-label="Task ID"
              value={newTaskId}
              onChange={(e) => setNewTaskId(e.target.value)}
              className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
            />
          </div>

          <div>
            <label htmlFor="init-repo-path" className="block text-slate-400 font-mono mb-1">Target Repository Path</label>
            <input
              id="init-repo-path"
              type="text"
              aria-label="Target Repository Path"
              value={newRepoPath}
              onChange={(e) => setNewRepoPath(e.target.value)}
              placeholder="Absolute path to target repository..."
              className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
            />
          </div>

          <div>
            <label htmlFor="init-requirement" className="block text-slate-400 font-mono mb-1">Requirement Prompt</label>
            <textarea
              id="init-requirement"
              rows={3}
              aria-label="Requirement Prompt"
              value={newRequirement}
              onChange={(e) => setNewRequirement(e.target.value)}
              placeholder="Describe the coding requirement..."
              className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="init-target-branch" className="block text-slate-400 font-mono mb-1">Target Branch</label>
              <input
                id="init-target-branch"
                type="text"
                aria-label="Target Branch"
                value={newTargetBranch}
                onChange={(e) => setNewTargetBranch(e.target.value)}
                className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
              />
            </div>
            <div>
              <label htmlFor="init-specialist-role" className="block text-slate-400 font-mono mb-1">Specialist Role</label>
              <select
                id="init-specialist-role"
                aria-label="Specialist Role"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
              >
                <option value="DOMAIN_LOGIC_AGENT">DOMAIN_LOGIC_AGENT</option>
                <option value="BACKEND_INFRA_AGENT">BACKEND_INFRA_AGENT</option>
                <option value="UI_UX_AGENT">UI_UX_AGENT</option>
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="init-inspected-files" className="block text-slate-400 font-mono mb-1">
              Inspected Files (Anti-Summary Invariant)
            </label>
            <input
              id="init-inspected-files"
              type="text"
              aria-label="Inspected Files"
              value={newInspectedFiles}
              onChange={(e) => setNewInspectedFiles(e.target.value)}
              className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
            />
          </div>

          <div>
            <label htmlFor="init-target-files" className="block text-slate-400 font-mono mb-1">Target Files to Modify</label>
            <input
              id="init-target-files"
              type="text"
              aria-label="Target Files to Modify"
              value={newTargetFiles}
              onChange={(e) => setNewTargetFiles(e.target.value)}
              className="w-full bg-black/50 border border-white/10 rounded px-3 py-1.5 text-white font-mono"
            />
          </div>

          {/* Committee Debate Controls */}
          <div className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableCommittee}
                  onChange={(e) => setEnableCommittee(e.target.checked)}
                  className="rounded border-white/20 bg-black/40 text-indigo-600 focus:ring-indigo-500"
                />
                <span className="text-white font-semibold flex items-center gap-1.5">
                  <Users className="h-3.5 w-3.5 text-indigo-400" />
                  Enable Committee Debate (Phase 85)
                </span>
              </label>
              <span className="text-[10px] text-indigo-300 font-mono">Consensus Gate</span>
            </div>
            {enableCommittee && (
              <div className="flex items-center gap-2.5 pt-1 text-[11px] text-slate-300">
                <span className="text-slate-400 font-mono">Deliberation:</span>
                <select
                  aria-label="Deliberation rounds"
                  value={debateRounds}
                  onChange={(e) => setDebateRounds(Number(e.target.value))}
                  className="bg-black/60 border border-white/15 rounded px-2 py-1 text-white font-mono text-xs"
                >
                  <option value={1}>1 Round (Fast Review)</option>
                  <option value={2}>2 Rounds (In-Depth Critique)</option>
                  <option value={3}>3 Rounds (Exhaustive Consensus)</option>
                </select>
                <span className="text-slate-400 text-[10px]">Auto-engages Architect, Security, QA</span>
              </div>
            )}
          </div>

          {/* Dynamic Reasoning & Offline Controls (Phase 86) */}
          <div className="rounded-lg border border-purple-500/30 bg-purple-500/10 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={offlineMode}
                  onChange={(e) => setOfflineMode(e.target.checked)}
                  className="rounded border-white/20 bg-black/40 text-purple-600 focus:ring-purple-500"
                />
                <span className="text-white font-semibold flex items-center gap-1.5">
                  🔒 Air-Gapped Offline Mode (Phase 86)
                </span>
              </label>
              <span className="text-[10px] text-purple-300 font-mono">Ollama Local</span>
            </div>
            <div className="flex items-center justify-between gap-3 pt-1 text-[11px]">
              <span className="text-slate-400 font-mono">Thinking Budget:</span>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  aria-label="Thinking budget tokens"
                  value={thinkingBudget}
                  onChange={(e) => handleBudgetChange(e.target.value)}
                  step={1024}
                  min={0}
                  max={32768}
                  className="w-24 bg-black/60 border border-white/15 rounded px-2 py-0.5 text-white font-mono text-xs text-right"
                />
                <span className="text-slate-400 font-mono text-[10px]">tokens</span>
              </div>
            </div>
          </div>

          {/* Federated P2P Mesh Controls (Phase 87) */}
          <div className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useMesh}
                  onChange={(e) => setUseMesh(e.target.checked)}
                  className="rounded border-white/20 bg-black/40 text-cyan-600 focus:ring-cyan-500"
                />
                <span className="text-white font-semibold flex items-center gap-1.5">
                  🌐 Federated P2P Mesh (Phase 87)
                </span>
              </label>
              <span className="text-[10px] text-cyan-300 font-mono">Worktree Cluster</span>
            </div>
            <p className="text-[10px] text-slate-400">
              Offload reasoning debate turns & test ladders across decentralized peer nodes
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/10">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={onSubmit}
            disabled={loading || !newRequirement}
            className="bg-indigo-600 hover:bg-indigo-500 text-white"
          >
            Submit & Precheck
          </Button>
        </div>
      </div>
    </div>
  );
}
