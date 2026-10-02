export type VerificationReceiptItem = {
  step_name: string;
  command: string;
  exit_code: number;
  status: string;
  stdout_snippet: string;
  stderr_snippet: string;
  duration_ms: number;
  timestamp: string;
};

export type DebateSpeechTurnItem = {
  speaker_role: string;
  target_role?: string | null;
  round_index: number;
  turn_index: number;
  content: string;
  critique_points: string[];
  score_impact: number;
  reasoning_content?: string | null;
  reasoning_tokens?: number;
  timestamp: string;
};

export type DebateRoundItem = {
  round_index: number;
  turns: DebateSpeechTurnItem[];
  round_summary: string;
};

export type CommitteeConsensusScorecardItem = {
  architectural_integrity: number;
  security_assurance: number;
  test_thoroughness: number;
  composite_score: number;
  total_reasoning_tokens?: number;
  decision: string;
  dissenting_opinions: string[];
  recommended_actions: string[];
};

export type CommitteeDebateItem = {
  debate_id: string;
  task_id: string;
  committee_members: string[];
  rounds: DebateRoundItem[];
  consensus_scorecard: CommitteeConsensusScorecardItem;
  duration_ms: number;
  timestamp: string;
};

export type SelfHealingAttemptItem = {
  attempt_number: number;
  strategy: string;
  error_symptom?: string;
  fix_description: string;
  healed: boolean;
  precedents_used?: string[];
  timestamp: string;
};

export type RollbackReceiptItem = {
  task_id: string;
  worktree_path: string;
  branch_name: string;
  restored_base_commit: string;
  untracked_files_purged: string[];
  restoration_status: string;
  canonical_clean: boolean;
  timestamp: string;
};

export type TaskDetailResponse = {
  status: string;
  task_id: string;
  request: {
    task_id: string;
    repository_path: string;
    requirement_prompt: string;
    base_branch: string;
    target_branch: string;
    inspected_files: string[];
    target_files: string[];
    allowed_roles: string[];
    enable_committee?: boolean;
    debate_rounds?: number;
    committee_roles?: string[];
  };
  plan?: {
    task_id: string;
    plan_summary: string;
    target_files: string[];
    assigned_role: string;
    test_strategy: string[];
    human_approved: boolean;
    approval_token?: string;
  } | null;
  committee_debate?: CommitteeDebateItem | null;
  result: {
    task_id: string;
    status: string;
    current_stage: string;
    stage_history: Array<{ stage: string; timestamp: string; detail: string }>;
    committee_debate?: CommitteeDebateItem | null;
    receipts: VerificationReceiptItem[];
    self_healing_attempts?: SelfHealingAttemptItem[];
    rollback_receipt?: RollbackReceiptItem | null;
    pr_payload?: {
      title: string;
      body: string;
      head_branch: string;
      base_branch: string;
      commit_hash: string;
      changed_files: string[];
      pr_url?: string;
      merkle_root?: string;
    } | null;
    error_message?: string | null;
  };
  preservation_receipt?: {
    receipt_id: string;
    repository_path: string;
    is_preserved: boolean;
    initial_head: string;
  };
};

export type TaskListItem = {
  task_id: string;
  stage: string;
  status: string;
  requirement: string;
  target_branch: string;
  has_plan: boolean;
  plan_approved: boolean;
  created_at: string;
};

export const STAGES = [
  { id: "INTAKE", label: "Intake", desc: "Requirement & Anti-Summary Preflight" },
  { id: "PRECHECK", label: "Precheck", desc: "Host Repo Snapshot & Preservation" },
  { id: "COMMITTEE_DEBATE", label: "Committee Debate", desc: "Multi-Agent Consensus Deliberation" },
  { id: "PLAN_AND_GATE", label: "Architecture Gate", desc: "Stop-and-Wait Human Approval" },
  { id: "ISOLATED_MUTATION", label: "Worktree Mutation", desc: "Native Git Isolation & ScopeGuard" },
  { id: "VERIFY_AND_EVIDENCE", label: "Verification Ladder", desc: "Multi-Tier Objective Tests" },
  { id: "SELF_HEALING", label: "Self-Healing", desc: "Autonomous Diagnostic Loop & Auto-Rollback" },
  { id: "DRAFT_PR_EXPORT", label: "Draft PR Export", desc: "Merkle Root & Signed Patch" },
];
