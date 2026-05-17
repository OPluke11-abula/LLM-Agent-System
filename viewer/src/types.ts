export type TaskStatus = "pending" | "in_progress" | "completed";
export type Lang = "zh" | "en";
export type ThemeId = "dark" | "tokyo" | "light" | "forest" | "beige";
export type SkillCategory = "backend" | "mobile" | "testing" | "quality";
export type SettingsTabId = "general" | "docs" | "guide";

export type AgentTask = {
  id: string;
  description: string;
  status: TaskStatus;
  dependencies: string[];
  ai_feedback?: string | null;
  tasks?: AgentTask[];
};

export type AgentMemory = {
  tasks: AgentTask[];
};

export type Workspace = {
  id: string;
  name: string;
  lang: string;
  path: string;
};

export type StatusLabels = {
  pending: string;
  inProgress: string;
  completed: string;
};

export type TaskNodeLabels = StatusLabels & {
  feedbackBadge: string;
};

export type TaskNodeData = {
  id: string;
  description: string;
  status: TaskStatus;
  dependencies: string[];
  ai_feedback?: string | null;
  labels: TaskNodeLabels;
  isHighlighted?: boolean;
  isDimmed?: boolean;
  onStatusChange: (id: string, status: TaskStatus) => void;
};

export type TaskVisualState = {
  isHighlighted: boolean;
  isDimmed: boolean;
};

export type ActivityLogType =
  | "workspace-loaded"
  | "workspace-synced"
  | "topology-updated"
  | "task-status"
  | "task-description"
  | "task-created"
  | "task-deleted"
  | "save-error";

export type ActivityLogEntry = {
  id: string;
  timestamp: string;
  type: ActivityLogType;
  workspaceId: string;
  workspaceName: string;
  taskId?: string;
  parentTaskId?: string;
  taskDescription?: string;
  fromStatus?: TaskStatus;
  toStatus?: TaskStatus;
  taskCount?: number;
  removedCount?: number;
  detail?: string;
};

export type ActivityLogInput = Omit<ActivityLogEntry, "id" | "timestamp">;

export type GuideItem = {
  title: string;
  body: string;
};

export type ThemeLabels = Record<ThemeId, string>;

export type TranslationMessages = {
  appTitle: string;
  taskFlow: string;
  rules: string;
  mods: string;
  settings: string;
  taskDetails: string;
  taskId: string;
  desc: string;
  deps: string;
  noDeps: string;
  aiFeedback: string;
  pending: string;
  inProgress: string;
  completed: string;
  feedbackBadge: string;
  copy: string;
  aiRules: string;
  addRule: string;
  addRuleTitle: string;
  addRulePlaceholder: string;
  deleteRuleTitle: string;
  deleteRuleConfirm: string;
  confirm: string;
  cancel: string;
  agentsMdToggle: string;
  agentsMdDesc: string;
  skillsTitle: string;
  skillsDesc: string;
  catBackend: string;
  catMobile: string;
  catTesting: string;
  catQuality: string;
  settingsTitle: string;
  generalSettingsTab: string;
  usageGuideTab: string;
  aiGuideTab: string;
  langLabel: string;
  themeLabel: string;
  themes: ThemeLabels;
  workspaces: string;
  addWorkspace: string;
  removeWs: string;
  wsName: string;
  wsLang: string;
  wsPath: string;
  wsPathPlaceholder: string;
  aiHowTitle: string;
  aiHowBody: string;
  activeWs: string;
  howItWorks: string;
  howSteps: GuideItem[];
  aiGuideTitle: string;
  aiGuideSteps: GuideItem[];
  opManual: string;
  opSteps: GuideItem[];
  aiTipsTitle: string;
  aiTipsDesc: string;
  tips: GuideItem[];
};

export type SkillDefinition = {
  id: string;
  cat: SkillCategory;
  zh: string;
  en: string;
};

export type ThemeDefinition = {
  id: ThemeId;
  accentNode: string;
};

export type TopologyNodeType = "session_root" | "agent" | "handoff" | "tool_call" | "hitl_gate" | "error";
export type TopologyEdgeType = "handoff" | "tool" | "rbac" | "error" | "hitl";
export type TopologyStatus = "pending" | "running" | "completed" | "error" | "awaiting_approval";

export type TopologyPayload = {
  name?: string;
  description?: string;
  input?: unknown;
  output?: unknown;
  rbac_role?: string;
  error_count?: number;
  human_notes?: string;
  token_used?: number;
  duration_ms?: number | null;
  [key: string]: unknown;
};

export type TopologyEvent = {
  event_id: string;
  timestamp: string;
  session_id: string;
  node_id: string;
  parent_node_id: string | null;
  node_type: TopologyNodeType;
  edge_type: TopologyEdgeType | null;
  status: TopologyStatus;
  payload: TopologyPayload;
};

export type TopologyState = {
  schema_version: string;
  session_id: string;
  started_at: string;
  updated_at: string;
  stats: {
    total_nodes: number;
    completed: number;
    running: number;
    pending: number;
    errors: number;
    total_tokens: number;
    total_duration_ms: number;
  };
  nodes: TopologyEvent[];
  edges: Array<{
    id: string;
    source: string;
    target: string;
    edge_type: TopologyEdgeType;
    label: string;
  }>;
};

export type TopologyNodeData = {
  event: TopologyEvent;
  label: string;
  description: string;
  isDimmed?: boolean;
  onOpen: (event: TopologyEvent) => void;
};

export type TopologyEdgeData = {
  edgeType: TopologyEdgeType;
  label?: string;
};
