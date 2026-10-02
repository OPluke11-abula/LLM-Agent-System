import { Activity } from "./ui/icons";
import { PipelineHeaderBanner } from "./pipeline/PipelineHeaderBanner";
import { PipelineStageStepper } from "./pipeline/PipelineStageStepper";
import { CommitteeDebateCard } from "./pipeline/CommitteeDebateCard";
import { ApprovalGateCard } from "./pipeline/ApprovalGateCard";
import { VerificationLadderCard } from "./pipeline/VerificationLadderCard";
import { TasksRail } from "./pipeline/TasksRail";
import { TaskCreationModal } from "./pipeline/TaskCreationModal";
import { BenchmarkModal } from "./pipeline/BenchmarkModal";
import { useCodingPipeline } from "../hooks/useCodingPipeline";

interface CodingPipelineViewProps {
  lang?: string;
  activeWorkspacePath?: string;
}

export function CodingPipelineView({ lang = "zh", activeWorkspacePath }: CodingPipelineViewProps) {
  const {
    tasks,
    selectedTaskId,
    setSelectedTaskId,
    taskDetail,
    loading,
    wsConnected,
    approvalToken,
    setApprovalToken,
    actionMessage,
    showBenchmarkModal,
    setShowBenchmarkModal,
    benchmarkScorecard,
    runningBenchmark,
    showCreateModal,
    setShowCreateModal,
    formState,
    fetchTasks,
    fetchTaskDetail,
    handleTriggerDebate,
    fetchLatestBenchmark,
    handleRunBenchmark,
    handleCreateTask,
    handleApproveGate,
  } = useCodingPipeline(activeWorkspacePath);

  return (
    <div className="flex h-full flex-col overflow-y-auto p-4 md:p-6 space-y-6">
      {/* Top Banner */}
      <PipelineHeaderBanner
        lang={lang}
        wsConnected={wsConnected}
        onSync={() => {
          fetchTasks();
          if (selectedTaskId) fetchTaskDetail(selectedTaskId);
        }}
        onOpenBenchmark={() => {
          setShowBenchmarkModal(true);
          fetchLatestBenchmark();
        }}
        onOpenCreateModal={() => setShowCreateModal(true)}
      />

      {actionMessage && (
        <div className="rounded-lg border border-indigo-500/40 bg-indigo-500/10 px-4 py-2.5 text-xs text-indigo-200 flex items-center gap-2">
          <Activity className="h-4 w-4 animate-spin text-indigo-400" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Main Grid: Left Tasks Rail + Right Pipeline Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-4 space-y-4">
          <TasksRail
            tasks={tasks}
            selectedTaskId={selectedTaskId}
            onSelectTask={setSelectedTaskId}
          />
        </div>

        <div className="lg:col-span-8 space-y-6">
          {taskDetail ? (
            <>
              <PipelineStageStepper taskDetail={taskDetail} />
              <CommitteeDebateCard
                taskDetail={taskDetail}
                lang={lang}
                onTriggerDebate={() => handleTriggerDebate(selectedTaskId!)}
                loading={formState.triggeringDebate}
              />
              <ApprovalGateCard
                taskDetail={taskDetail}
                approvalToken={approvalToken}
                setApprovalToken={setApprovalToken}
                loading={loading}
                onApprove={handleApproveGate}
              />
              <VerificationLadderCard taskDetail={taskDetail} />
            </>
          ) : (
            <div className="text-center py-16 text-slate-400 text-xs">
              Select a task from the list or create a new coding task.
            </div>
          )}
        </div>
      </div>

      <TaskCreationModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        newTaskId={formState.newTaskId}
        setNewTaskId={formState.setNewTaskId}
        newRepoPath={formState.newRepoPath}
        setNewRepoPath={formState.setNewRepoPath}
        newRequirement={formState.newRequirement}
        setNewRequirement={formState.setNewRequirement}
        newTargetBranch={formState.newTargetBranch}
        setNewTargetBranch={formState.setNewTargetBranch}
        newRole={formState.newRole}
        setNewRole={formState.setNewRole}
        newInspectedFiles={formState.newInspectedFiles}
        setNewInspectedFiles={formState.setNewInspectedFiles}
        newTargetFiles={formState.newTargetFiles}
        setNewTargetFiles={formState.setNewTargetFiles}
        enableCommittee={formState.enableCommittee}
        setEnableCommittee={formState.setEnableCommittee}
        debateRounds={formState.debateRounds}
        setDebateRounds={formState.setDebateRounds}
        offlineMode={formState.offlineMode}
        setOfflineMode={formState.setOfflineMode}
        thinkingBudget={formState.thinkingBudget}
        setThinkingBudget={formState.setThinkingBudget}
        useMesh={formState.useMesh}
        setUseMesh={formState.setUseMesh}
        loading={loading}
        onSubmit={handleCreateTask}
      />

      <BenchmarkModal
        isOpen={showBenchmarkModal}
        onClose={() => setShowBenchmarkModal(false)}
        lang={lang}
        runningBenchmark={runningBenchmark}
        onRunBenchmark={handleRunBenchmark}
        benchmarkScorecard={benchmarkScorecard}
      />
    </div>
  );
}
