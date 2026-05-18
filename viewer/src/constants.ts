import type {
  AgentMemory,
  Lang,
  SkillCategory,
  SkillDefinition,
  ThemeDefinition,
  TranslationMessages,
  Workspace,
} from "./types";

export const T: Record<Lang, TranslationMessages> = {
  zh: {
    appTitle: "控制中心",
    taskFlow: "任務流程",
    rules: "規則",
    mods: "模組",
    settings: "設定",
    taskDetails: "任務詳情",
    taskId: "任務 ID",
    desc: "描述",
    deps: "依賴項目",
    noDeps: "無 — 根任務",
    aiFeedback: "AI 回饋",
    pending: "待處理",
    inProgress: "執行中",
    completed: "已完成",
    feedbackBadge: "💬 含 AI 回饋",
    copy: "📋 複製",
    aiRules: "AI 指令規則",
    addRule: "+ 新增指令",
    addRuleTitle: "新增 AI 指令",
    addRulePlaceholder: "輸入 AI 指令內容...",
    deleteRuleTitle: "刪除指令",
    deleteRuleConfirm: "確定要刪除這條指令嗎？",
    confirm: "確認",
    cancel: "取消",
    agentsMdToggle: "啟用 AGENTS.md 技能路由",
    agentsMdDesc: "啟用後，AI 將依照 AGENTS.md 規則自動選用對應技能提示詞。",
    skillsTitle: "技能提示詞",
    skillsDesc: "勾選後，所選技能將附加到 AI 指令中。",
    catBackend: "後端 & 架構",
    catMobile: "行動 & UI/UX",
    catTesting: "測試 & 文件",
    catQuality: "程式品質",
    settingsTitle: "設定",
    generalSettingsTab: "一般設定",
    usageGuideTab: "使用說明",
    aiGuideTab: "AI 指南",
    langLabel: "介面語言",
    themeLabel: "介面主題",
    themes: {
      light: "白色",
      tokyo: "Tokyo 電子風",
      dark: "黑色",
      forest: "森林綠",
      beige: "米棕色",
    },
    workspaces: "工作區",
    addWorkspace: "+ 新增工作區",
    removeWs: "移除",
    wsName: "工作區名稱",
    wsLang: "程式語言",
    wsPath: "JSON 路徑",
    wsPathPlaceholder: "D:\\Projects\\your-ai-project\\workspace",
    aiHowTitle: "AI 如何區分工作區？",
    aiHowBody: "每個工作區對應一個獨立的 agent_memory.json 路徑。讓 AI 代理（Codex、Antigravity 等）讀寫對應工作區的 JSON 路徑，即可讓多個 AI 各自操作獨立的任務圖，互不干擾。",
    activeWs: "當前工作區",
    howItWorks: "運作原理",
    howSteps: [
      {
        title: "共用 JSON 任務檔案",
        body: "Codex、Antigravity 等 AI 代理與本應用程式共享同一個 agent_memory.json。AI 寫入任務與回饋，使用者從 UI 更新狀態，兩者即時同步。",
      },
      {
        title: "檔案即時監聽",
        body: "Tauri 後端使用 notify crate 監聽 workspace 目錄。任何外部程式（包括 AI）修改 JSON 後，圖表會在毫秒內自動重新渲染。",
      },
      {
        title: "多 AI 並行協作",
        body: "Codex 可處理程式碼生成，Antigravity 可處理規劃與回顧。兩者均透過讀寫 agent_memory.json 的 status 與 ai_feedback 欄位來交換上下文，不需要直接通訊。",
      },
      {
        title: "人工監控",
        body: "使用者在 Task Flow 視圖中即時觀察 AI 進度，點擊節點改變狀態即可指揮 AI 進行下一步，無需手動編輯 JSON。",
      },
    ],
    aiGuideTitle: "與 AI 代理 (Codex/Antigravity) 協作指南",
    aiGuideSteps: [
      {
        title: "1. 配置獨立 Workspace",
        body: "在上方『工作區』區塊加入新專案，填寫專屬的 JSON 路徑（例如 D:\\ProjectA\\workspace）。輸入完畢後記得點擊「確認」按鈕來套用新路徑。",
      },
      {
        title: "🧠 Antigravity（規劃師）指南",
        body: "Antigravity 負責理解需求、拆解任務，並寫入 JSON。請對 Antigravity 下達類似以下指令：\n\n『你是一位 AI 開發規劃師。請幫我規劃一個登入系統，並將規劃結果更新到 D:\\Projects\\my-project\\workspace\\agent_memory.json。\n\n⚠️ 嚴格格式要求 — 每個任務節點必須且只能包含以下欄位：\n{  \"id\": \"task-001\",\n   \"description\": \"任務描述文字\",\n   \"status\": \"pending\",\n   \"dependencies\": [],\n   \"ai_feedback\": \"\" }\n\n• id — 唯一識別碼（如 task-001, task-002）\n• description — 任務說明（必填，圖表節點顯示此欄位）\n• status — 只能是 pending / in_progress / completed\n• dependencies — 前置任務 id 陣列（第一個任務設 []）\n• ai_feedback — 完成後的反省或備註\n\n❌ 禁止新增 title、design、findings 等自訂欄位，否則 UI 無法正確渲染。』",
      },
      {
        title: "⚙️ Codex（執行者）指南",
        body: "Codex 負責撰寫實際程式碼。請對 Codex 下達類似以下指令：\n\n『請讀取 D:\\Projects\\my-project\\workspace\\agent_memory.json，尋找 status 為 in_progress 的任務。執行該任務後，如果完成，請將 JSON 中的狀態改為 completed，並在 ai_feedback 留下你修改了哪些檔案或遭遇的問題。』",
      },
      {
        title: "🧑‍💻 人類（你）的日常工作循環",
        body: "① 規劃階段：你要求 Antigravity 規劃任務。它將任務寫入 JSON（狀態為 pending 🟡）。\n② 監控與批准：你在 Topology Viewer 中看到新長出的圖表節點。點擊你想開始的任務，手動將狀態切換為 in_progress 🔵。這代表了你的批准執行。\n③ 執行階段：你命令 Codex 去處理 in_progress 的任務。\n④ 回顧階段：Codex 完成後，節點在 UI 變成 completed 🟢。點擊節點，右側滑出面板可閱讀 ai_feedback，確認 AI 的想法，並根據結果進行下一波規劃。",
      },
      {
        title: "💡 確保 AI 吃到設定 (AGENTS.md)",
        body: "在開啟對話的當下，你必須給 AI 初始指令：「請詳閱工作目錄下的 AGENTS.md 並遵守規範」，AI 才會啟動並吃到所有的規則。",
      },
    ],
    opManual: "操作說明",
    opSteps: [
      {
        title: "載入任務",
        body: "Tauri 啟動時自動讀取 workspace/agent_memory.json。設定 AGENT_WORKSPACE_DIR 可指向自訂目錄。",
      },
      {
        title: "任務節點互動",
        body: "點選節點 → 右側詳情面板滑出。透過下拉選單改變狀態 → 即時寫回 JSON。",
      },
      {
        title: "多工作區支援",
        body: "在設定中新增多個工作區，每個工作區有獨立的任務圖。",
      },
      {
        title: "技能提示詞",
        body: "在模組頁勾選需要的技能，AI 閱讀 AGENTS.md 後會按照對應場景載入提示詞。",
      },
    ],
    aiTipsTitle: "AI 對話技巧",
    aiTipsDesc: "提煉自實際工作流，點擊展開。",
    tips: [
      {
        title: "📥 先餵資料，再說「stop」",
        body: "在要求 AI 執行任務之前，先分批提供所有背景資料，明確告知待命，讓 AI 充分吸收整體脈絡。",
      },
      {
        title: "📌 版本鎖定規則",
        body: "在 AGENTS.md 中明確列出每種語言的最新穩定版本，強制 AI 使用最新語法。",
      },
      {
        title: "🧠 注入 .agent 技能庫",
        body: "將領域知識技能目錄提前塞入 .agent/skills/，讓 AI 在開發前讀取對應技能。",
      },
      {
        title: "🔄 結構化 JSON 溝通",
        body: "善用 agent_memory.json 的節點結構讓 AI 明確記錄每步，透過本工具視覺化整體進度。",
      },
      {
        title: "🎯 小批次迭代原則",
        body: "每次只讓 AI 處理一個明確子任務，完成後驗收再進行下一步。",
      },
    ],
    llmConfigTitle: "LLM 模型與服務設定",
    llmProviderLabel: "供應商 (Provider)",
    llmModelLabel: "模型 (Model)",
    llmApiKeyLabel: "API 金鑰 (API Key)",
    llmBaseUrlLabel: "自訂端點 (Base URL)",
    saveConfigBtn: "儲存模型設定",
    configSavedToast: "設定已成功更新！系統將立即套用新模型。",
  },
  en: {
    appTitle: "Control Center",
    taskFlow: "Task Flow",
    rules: "Rules",
    mods: "MODs",
    settings: "Settings",
    taskDetails: "Task Details",
    taskId: "Task ID",
    desc: "Description",
    deps: "Dependencies",
    noDeps: "None — root task",
    aiFeedback: "AI Feedback",
    pending: "Pending",
    inProgress: "In Progress",
    completed: "Completed",
    feedbackBadge: "💬 AI Feedback attached",
    copy: "📋 Copy",
    aiRules: "AI Instruction Rules",
    addRule: "+ Add Rule",
    addRuleTitle: "Add AI Instruction",
    addRulePlaceholder: "Enter AI instruction...",
    deleteRuleTitle: "Delete Instruction",
    deleteRuleConfirm: "Are you sure you want to delete this instruction?",
    confirm: "Confirm",
    cancel: "Cancel",
    agentsMdToggle: "Enable AGENTS.md Skill Routing",
    agentsMdDesc: "When enabled, the AI will automatically select skill prompts based on AGENTS.md routing rules.",
    skillsTitle: "Active Skill Prompts",
    skillsDesc: "Checked skills will be appended to AI instructions automatically.",
    catBackend: "Backend & Architecture",
    catMobile: "Mobile & UI/UX",
    catTesting: "Testing & Docs",
    catQuality: "Code Quality",
    settingsTitle: "Settings",
    generalSettingsTab: "General",
    usageGuideTab: "Guide",
    aiGuideTab: "AI Guide",
    langLabel: "UI Language",
    themeLabel: "UI Theme",
    themes: {
      light: "White",
      tokyo: "Tokyo Electronic",
      dark: "Black",
      forest: "Forest Green",
      beige: "Beige",
    },
    workspaces: "Workspaces",
    addWorkspace: "+ Add Workspace",
    removeWs: "Remove",
    wsName: "Workspace Name",
    wsLang: "Language",
    wsPath: "JSON Path",
    wsPathPlaceholder: "D:\\Projects\\your-ai-project\\workspace",
    aiHowTitle: "How does AI distinguish workspaces?",
    aiHowBody: "Each workspace maps to a unique agent_memory.json file path. Configure your AI agents (Codex, Antigravity, etc.) to read from and write to each workspace's designated JSON path. This lets multiple AIs operate on completely independent task graphs without interfering with each other.",
    activeWs: "Active Workspace",
    howItWorks: "How It Works",
    howSteps: [
      {
        title: "Shared JSON Task File",
        body: "Codex, Antigravity, and this app share the same agent_memory.json. AIs write tasks and feedback; users update status from the UI — everything syncs in real time.",
      },
      {
        title: "Live File Watching",
        body: "The Tauri backend uses the notify crate to watch the workspace directory. Any external program modifying the JSON causes the graph to re-render within milliseconds.",
      },
      {
        title: "Multi-AI Parallel Collaboration",
        body: "Codex handles code generation, Antigravity handles planning and review. Both exchange context through status and ai_feedback fields without direct communication.",
      },
      {
        title: "Human Oversight",
        body: "Users observe AI progress in real time. Clicking a node to change its status directly directs the AI to the next step — no manual JSON editing required.",
      },
    ],
    aiGuideTitle: "Collaboration Guide: Codex / Antigravity",
    aiGuideSteps: [
      {
        title: "1. Configure Workspace",
        body: "Add a new workspace and specify an absolute JSON path (e.g., D:\\Proj\\workspace) so your AI agents don't step on each other. Remember to click 'Confirm' after entering the path to apply the change.",
      },
      {
        title: "🧠 Antigravity (Planner) Guide",
        body: "Antigravity understands requirements, decomposes tasks, and writes them to JSON. Give it a prompt like:\n\n'You are an AI development planner. Plan a login system and update D:\\Projects\\my-project\\workspace\\agent_memory.json.\n\n⚠️ Strict format required — each task node must contain ONLY these fields:\n{  \"id\": \"task-001\",\n   \"description\": \"Task description text\",\n   \"status\": \"pending\",\n   \"dependencies\": [],\n   \"ai_feedback\": \"\" }\n\n• id — unique identifier (e.g. task-001, task-002)\n• description — task description (required, displayed on graph nodes)\n• status — must be pending / in_progress / completed\n• dependencies — array of prerequisite task ids (first task uses [])\n• ai_feedback — reflection or notes after completion\n\n❌ Do NOT add custom fields like title, design, findings, etc. The UI cannot render them.'",
      },
      {
        title: "⚙️ Codex (Executor) Guide",
        body: "Codex writes actual code. Give it a prompt like:\n\n'Read D:\\Projects\\my-project\\workspace\\agent_memory.json and find tasks with status in_progress. Execute the task, then change the JSON status to completed and leave a note in ai_feedback describing which files you modified or issues encountered.'",
      },
      {
        title: "🧑‍💻 Human (You) Daily Workflow",
        body: "① Planning: Ask Antigravity to plan tasks. It writes them to JSON (status: pending 🟡).\n② Monitor & Approve: New nodes appear in Topology Viewer. Click a task you want to start and switch it to in_progress 🔵 — this is your approval.\n③ Execution: Command Codex to handle in_progress tasks.\n④ Review: After Codex finishes, nodes turn completed 🟢. Click a node to open the detail panel, read ai_feedback, confirm the AI's work, then begin the next planning cycle.",
      },
      {
        title: "💡 Ensuring AI reads AGENTS.md",
        body: "This UI toggle prepares the markdown file, but you must still explicitly tell your AI: 'Read AGENTS.md and follow its rules' when you start the conversation.",
      },
    ],
    opManual: "Operating Manual",
    opSteps: [
      {
        title: "Load Tasks",
        body: "Tauri reads workspace/agent_memory.json on startup. Set AGENT_WORKSPACE_DIR to use a custom directory.",
      },
      {
        title: "Node Interaction",
        body: "Click a node → the detail panel slides out. Change status via dropdown → writes back to JSON instantly.",
      },
      {
        title: "Multi-Workspace Support",
        body: "Add multiple workspaces in Settings, each with its own independent task graph.",
      },
      {
        title: "Skill Prompts",
        body: "Check needed skills in MODs. The AI will load corresponding prompts based on AGENTS.md rules.",
      },
    ],
    aiTipsTitle: "AI Prompting Techniques",
    aiTipsDesc: "Extracted from real workflows. Click to expand.",
    tips: [
      {
        title: "📥 Feed Data First, Then Say 'stop'",
        body: "Before asking the AI to execute, feed all background data incrementally and tell it to stand by until you say 'stop'.",
      },
      {
        title: "📌 Lock Version Rules",
        body: "Clearly list the latest stable version of every language in AGENTS.md, forcing the AI to use current syntax.",
      },
      {
        title: "🧠 Inject .agent Skill Libraries",
        body: "Pre-load domain knowledge skill directories into .agent/skills/ so the AI reads them before development.",
      },
      {
        title: "🔄 Structured JSON Communication",
        body: "Use the node structure of agent_memory.json to let the AI explicitly record each step.",
      },
      {
        title: "🎯 Small Batch Iteration Principle",
        body: "Let the AI handle one clear sub-task at a time, verify, then proceed to the next.",
      },
    ],
    llmConfigTitle: "LLM Model Configuration",
    llmProviderLabel: "Provider",
    llmModelLabel: "Model",
    llmApiKeyLabel: "API Key",
    llmBaseUrlLabel: "Base URL",
    saveConfigBtn: "Save LLM Config",
    configSavedToast: "Configuration saved successfully! The new model is now active.",
  },
};

export const ALL_LANGS = [
  "TypeScript",
  "JavaScript",
  "Python",
  "Rust",
  "Go",
  "Dart",
  "Swift",
  "Kotlin",
  "C++",
  "C#",
  "Java",
  "Ruby",
  "PHP",
];

export const THEME_LIST: ThemeDefinition[] = [
  { id: "light", accentNode: "#0284c7" },
  { id: "tokyo", accentNode: "#ff2eff" },
  { id: "dark", accentNode: "#6366f1" },
  { id: "forest", accentNode: "#22c55e" },
  { id: "beige", accentNode: "#b45309" },
];

export const ALL_SKILLS: SkillDefinition[] = [
  { id: "backend-architect", cat: "backend", zh: "後端架構師", en: "Backend Architect" },
  { id: "api-design-principles", cat: "backend", zh: "API 設計原則", en: "API Design Principles" },
  { id: "data-pipeline-architect", cat: "backend", zh: "資料管線架構師", en: "Data Pipeline Architect" },
  { id: "fastapi-swagger-sync", cat: "backend", zh: "FastAPI Swagger 同步", en: "FastAPI Swagger Sync" },
  { id: "graphql-resolver-gen", cat: "backend", zh: "GraphQL 解析器生成", en: "GraphQL Resolver Gen" },
  { id: "api-contract-sync", cat: "backend", zh: "API 合約同步", en: "API Contract Sync" },
  { id: "react-native-expert", cat: "mobile", zh: "React Native 專家", en: "React Native Expert" },
  { id: "react-native-perf-boost", cat: "mobile", zh: "React Native 效能優化", en: "React Native Perf Boost" },
  { id: "mobile-sensor-integrator", cat: "mobile", zh: "行動感測器整合", en: "Mobile Sensor Integrator" },
  { id: "ui-ux-pro-max-skill", cat: "mobile", zh: "UI/UX 專業技能", en: "UI/UX Pro Max" },
  { id: "gamification-ui-kit", cat: "mobile", zh: "遊戲化 UI 套件", en: "Gamification UI Kit" },
  { id: "design-to-code-bridge", cat: "mobile", zh: "設計轉程式碼橋接", en: "Design to Code Bridge" },
  { id: "tdd-workflows-tdd-cycle", cat: "testing", zh: "TDD 工作流程", en: "TDD Workflows" },
  { id: "qa-auto-tester-pro", cat: "testing", zh: "QA 自動測試", en: "QA Auto Tester Pro" },
  { id: "doc-gen-pro", cat: "testing", zh: "文件生成器", en: "Doc Gen Pro" },
  { id: "code-refactoring-refactor-clean", cat: "quality", zh: "程式碼重構", en: "Code Refactoring" },
  { id: "code-review-ai-ai-review", cat: "quality", zh: "AI 程式碼審查", en: "Code Review AI" },
  { id: "python-ast-visualizer", cat: "quality", zh: "Python AST 視覺化", en: "Python AST Visualizer" },
  { id: "git-commit-standardizer", cat: "quality", zh: "Git 提交標準化", en: "Git Commit Standardizer" },
  { id: "python-algo-optimizer", cat: "quality", zh: "Python 演算法優化", en: "Python Algo Optimizer" },
];

export const CAT_KEYS: SkillCategory[] = ["backend", "mobile", "testing", "quality"];

export const DEFAULT_MEMORY: AgentMemory = {
  tasks: [
    {
      id: "task-001",
      description: "Initialize desktop topology viewer scaffold",
      status: "completed",
      dependencies: [],
      ai_feedback: "Tauri 2.0 + Vite scaffolded cleanly. Recommend pinning Rust edition to 2021.",
      tasks: [
        {
          id: "task-001-01",
          description: "Set up Tauri + React + Vite architecture",
          status: "completed",
          dependencies: ["task-001"],
        },
        {
          id: "task-001-02",
          description: "Create fixed sidebar and route shells",
          status: "completed",
          dependencies: ["task-001-01"],
        },
      ],
    },
    {
      id: "task-002",
      description: "Render DAG from agent memory with dagre auto-layout",
      status: "in_progress",
      dependencies: ["task-001-02"],
      ai_feedback: "Dagre LR layout wired. nodesep=60, ranksep=130. No overlaps on complex trees.",
      tasks: [
        {
          id: "task-002-01",
          description: "Map dependencies into directed edges",
          status: "completed",
          dependencies: ["task-002"],
        },
        {
          id: "task-002-02",
          description: "Display glowing status task cards",
          status: "in_progress",
          dependencies: ["task-002-01"],
          ai_feedback: "In-progress nodes now emit pulsing amber glow via CSS keyframe animation.",
        },
      ],
    },
    {
      id: "task-003",
      description: "Two-way sync: write status changes back to JSON",
      status: "completed",
      dependencies: ["task-002-02"],
      ai_feedback: "save_agent_memory Tauri IPC implemented. Optimistic UI update fires before async write.",
    },
    {
      id: "task-004",
      description: "Persist settings, rules and mods across sessions",
      status: "pending",
      dependencies: ["task-003"],
    },
  ],
};

export const EMPTY_MEMORY: AgentMemory = { tasks: [] };

export const DEFAULT_RULES = [
  "Please use the latest syntax for the current version of each programming language.",
  "Iterate on the existing code architecture. Do not create new files unless absolutely necessary.",
  "Operate with maximum efficiency and avoid any redundant or bloated code.",
];

export const DEFAULT_WORKSPACES: Workspace[] = [
  { id: "ws-default", name: "Project 1", lang: "TypeScript", path: "" },
];
