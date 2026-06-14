import { useState } from "react";
import type { Lang } from "../types";

export type OnboardingFinishPayload = {
  name: string;
  path: string;
};

type OnboardingWizardProps = {
  lang: Lang;
  onFinish: (payload: OnboardingFinishPayload) => void;
};

type WizardCopy = {
  badge: string;
  title: string;
  subtitle: string;
  start: string;
  setupTitle: string;
  setupBody: string;
  workspaceName: string;
  workspacePath: string;
  optionalHint: string;
  create: string;
  promptTitle: string;
  promptBody: string;
  copy: string;
  copied: string;
  finish: string;
  back: string;
  stepOne: string;
  stepTwo: string;
  stepThree: string;
  previewTitle: string;
  pathPreview: string;
  planCard: string;
  trackCard: string;
  reviewCard: string;
};

const COPY: Record<Lang, WizardCopy> = {
  zh: {
    badge: "首次啟動引導",
    title: "把 AI 的思考過程可視化",
    subtitle: "先建立你的第一個工作區，再把提示詞貼給 AI，讓它開始規劃可追蹤的任務 DAG。",
    start: "開始設定",
    setupTitle: "建立第一個工作區",
    setupBody: "工作區對應一個獨立的 `agent_memory.json` 來源。你可以先只填名稱，JSON 路徑之後再補。",
    workspaceName: "工作區名稱",
    workspacePath: "JSON 路徑",
    optionalHint: "可跳過。若填入資料夾路徑，Viewer 會讀寫其中的 `agent_memory.json`。",
    create: "建立",
    promptTitle: "複製 AI 提示詞",
    promptBody: "把這段指令貼給 AI，讓它開始規劃任務。",
    copy: "複製提示詞",
    copied: "已複製",
    finish: "完成，帶我看儀表板",
    back: "返回上一步",
    stepOne: "歡迎",
    stepTwo: "工作區",
    stepThree: "提示詞",
    previewTitle: "Demo Task DAG",
    pathPreview: "將使用的記憶檔",
    planCard: "讓規劃型 AI 先輸出結構化任務與依賴關係。",
    trackCard: "用 DAG 視圖追蹤哪些節點進行中、哪些節點完成。",
    reviewCard: "回頭讀取 `ai_feedback`，掌握 AI 真正做了什麼。",
  },
  en: {
    badge: "First-run setup",
    title: "Visualize how your AI thinks",
    subtitle: "Create your first workspace, then hand the prompt to your AI so it can start planning a trackable task DAG.",
    start: "Start setup",
    setupTitle: "Create your first workspace",
    setupBody: "Each workspace maps to one `agent_memory.json` source. You can set only the name now and add the JSON path later.",
    workspaceName: "Workspace name",
    workspacePath: "JSON path",
    optionalHint: "Optional. If you enter a folder path, the viewer will read and write `agent_memory.json` inside it.",
    create: "Create",
    promptTitle: "Copy the AI prompt",
    promptBody: "Paste this into your AI so it can start planning tasks.",
    copy: "Copy prompt",
    copied: "Copied",
    finish: "Finish and open dashboard",
    back: "Back",
    stepOne: "Welcome",
    stepTwo: "Workspace",
    stepThree: "Prompt",
    previewTitle: "Demo Task DAG",
    pathPreview: "Memory file path",
    planCard: "Let your planning AI produce structured tasks and dependency links first.",
    trackCard: "Use the DAG view to track which nodes are active and which ones are done.",
    reviewCard: "Read back `ai_feedback` so you can see what the AI actually changed.",
  },
  ja: {
    badge: "初回起動ガイド",
    title: "AIの思考プロセスを可視化する",
    subtitle: "最初のワークスペースを作成し、プロンプトをAIに渡して、追跡可能なタスクDAGの計画を開始させましょう。",
    start: "セットアップを開始",
    setupTitle: "最初のワークスペースを作成",
    setupBody: "各ワークスペースは1つの `agent_memory.json` ソースに対応します。今は名前だけを設定し、JSONパスは後で追加できます。",
    workspaceName: "ワークスペース名",
    workspacePath: "JSONパス",
    optionalHint: "スキップ可能。フォルダパスを入力すると、Viewerはその中の `agent_memory.json` を読み書きします。",
    create: "作成",
    promptTitle: "AIプロンプトをコピー",
    promptBody: "これをAIに貼り付けて、タスクの計画を開始させます。",
    copy: "プロンプトをコピー",
    copied: "コピーしました",
    finish: "完了してダッシュボードを表示",
    back: "戻る",
    stepOne: "ようこそ",
    stepTwo: "ワークスペース",
    stepThree: "プロンプト",
    previewTitle: "デモタスクDAG",
    pathPreview: "使用するメモリファイル",
    planCard: "計画型AIが最初に構造化されたタスクと依存関係リンクを出力するようにします。",
    trackCard: "DAGビューを使用して、アクティブなノードと完了したノードを追跡します。",
    reviewCard: "`ai_feedback` を読み返して、AIが実際に何を変更したかを把握します。",
  },
  fr: {
    badge: "Guide de premier démarrage",
    title: "Visualisez le processus de réflexion de l'IA",
    subtitle: "Créez votre premier espace de travail, puis fournissez l'invite à votre IA pour qu'elle commence à planifier un DAG de tâches traçable.",
    start: "Démarrer la configuration",
    setupTitle: "Créer votre premier espace de travail",
    setupBody: "Chaque espace de travail correspond à une source `agent_memory.json`. Vous pouvez définir uniquement le nom pour l'instant et ajouter le chemin JSON plus tard.",
    workspaceName: "Nom de l'espace de travail",
    workspacePath: "Chemin JSON",
    optionalHint: "Optionnel. Si vous entrez un chemin de dossier, le Viewer lira et écrira le fichier `agent_memory.json` à l'intérieur.",
    create: "Créer",
    promptTitle: "Copier l'invite de l'IA",
    promptBody: "Collez ceci dans votre IA pour qu'elle puisse commencer à planifier les tâches.",
    copy: "Copier l'invite",
    copied: "Copié",
    finish: "Terminer et ouvrir le tableau de bord",
    back: "Retour",
    stepOne: "Bienvenue",
    stepTwo: "Espace de travail",
    stepThree: "Invite",
    previewTitle: "Démo du DAG de Tâches",
    pathPreview: "Chemin du fichier mémoire",
    planCard: "Laissez votre IA de planification produire d'abord des tâches structurées et des liens de dépendance.",
    trackCard: "Utilisez la vue DAG pour suivre quels nœuds sont actifs et lesquels sont terminés.",
    reviewCard: "Lisez en retour `ai_feedback` pour voir ce que l'IA a réellement modifié.",
  },
};

function resolveMemoryFilePath(path: string) {
  const trimmed = path.trim();
  if (!trimmed) {
    return "D:\\Projects\\my-project\\workspace\\agent_memory.json";
  }

  const normalized = trimmed.replace(/[\\/]+$/, "");
  if (normalized.toLowerCase().endsWith("agent_memory.json")) {
    return normalized;
  }

  return `${normalized}\\agent_memory.json`;
}

function buildPlannerPrompt(workspaceName: string, workspacePath: string, lang: Lang) {
  const target = resolveMemoryFilePath(workspacePath);
  const name = workspaceName.trim() || (lang === "zh" ? "My First Project" : "My First Project");

  if (lang === "zh") {
    return [
      "你是一位 AI 開發規劃師。",
      `請為「${name}」拆解一份可執行的任務計畫，並將結果更新到：`,
      target,
      "",
      "請嚴格輸出到以下 JSON 結構中，每個任務節點只能包含這些欄位：",
      "{",
      '  "id": "task-001",',
      '  "description": "任務描述文字",',
      '  "status": "pending",',
      '  "dependencies": [],',
      '  "ai_feedback": "",',
      '  "tasks": []',
      "}",
      "",
      "規則：",
      "1. status 只能是 pending / in_progress / completed",
      "2. dependencies 必須是前置任務 id 陣列",
      "3. description 必填，請寫得具體可執行",
      "4. 可以用 tasks 建立子任務",
      "5. 不要新增 title、notes、findings 等自訂欄位",
      "",
      "請先規劃 1 個主流程，再補上必要的子任務與依賴關係。",
    ].join("\n");
  }

  if (lang === "ja") {
    return [
      "あなたは AI 開発プランナーです。",
      `「${name}」のために実行可能なタスク計画を分解し、結果を次のパスに書き込んでください：`,
      target,
      "",
      "タスクは厳格に以下の JSON 形式で出力し、各タスクノードには以下のフィールドのみを含める必要があります：",
      "{",
      '  "id": "task-001",',
      '  "description": "タスクの説明",',
      '  "status": "pending",',
      '  "dependencies": [],',
      '  "ai_feedback": "",',
      '  "tasks": []',
      "}",
      "",
      "ルール：",
      "1. status は pending / in_progress / completed のいずれかである必要があります",
      "2. dependencies は前提条件タスクIDの配列である必要があります",
      "3. description は必須で、具体的かつ実行可能である必要があります",
      "4. 必要に応じて tasks を使用してネストされたサブタスクを作成できます",
      "5. title、notes、findings などのカスタムフィールドは追加しないでください",
      "",
      "最初に1つのメインフローを計画し、それから必要なサブタスクと依存関係を追加してください。",
    ].join("\n");
  }

  if (lang === "fr") {
    return [
      "Vous êtes un planificateur de développement IA.",
      `Décomposez « ${name} » en un plan de tâches exécutables et mettez à jour le résultat à :`,
      target,
      "",
      "Écrivez les tâches strictement dans cette structure JSON. Chaque nœud de tâche ne peut contenir que ces champs :",
      "{",
      '  "id": "task-001",',
      '  "description": "Description de la tâche",',
      '  "status": "pending",',
      '  "dependencies": [],',
      '  "ai_feedback": "",',
      '  "tasks": []',
      "}",
      "",
      "Règles :",
      "1. status doit être pending / in_progress / completed",
      "2. dependencies doit être un tableau d'identifiants de tâches prérequises",
      "3. description est obligatoire et doit être exploitable",
      "4. Utilisez tasks pour les sous-tâches imbriquées si nécessaire",
      "5. N'ajoutez pas de champs personnalisés comme title, notes ou findings",
      "",
      "Commencez par un flux principal, puis ajoutez les sous-tâches et les dépendances nécessaires.",
    ].join("\n");
  }

  return [
    "You are an AI development planner.",
    `Break down "${name}" into an actionable task plan and update the result at:`,
    target,
    "",
    "Write tasks strictly in this JSON shape. Each task node may contain only these fields:",
    "{",
    '  "id": "task-001",',
    '  "description": "Task description",',
    '  "status": "pending",',
    '  "dependencies": [],',
    '  "ai_feedback": "",',
    '  "tasks": []',
    "}",
    "",
    "Rules:",
    "1. status must be pending / in_progress / completed",
    "2. dependencies must be an array of prerequisite task ids",
    "3. description is required and must be actionable",
    "4. Use tasks for nested subtasks when needed",
    "5. Do not add custom fields like title, notes, or findings",
    "",
    "Start with one main flow, then add the needed subtasks and dependencies.",
  ].join("\n");
}

function DemoDagCard() {
  return (
    <div className="metric-card relative h-[320px] overflow-hidden p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--t3)" }}>Topology Preview</p>
          <p className="mt-2 text-lg font-semibold" style={{ color: "var(--t1)" }}>AI planning in motion</p>
        </div>
        <div className="rounded-md border px-3 py-1 text-[11px] font-semibold" style={{ borderColor: "var(--border-c)", background: "var(--accent-bg)", color: "var(--accent-strong)" }}>
          LIVE DAG
        </div>
      </div>

      <div className="flow-canvas relative h-[230px] rounded-lg border" style={{ borderColor: "var(--border-c)" }}>
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 720 300" fill="none" aria-hidden>
          <defs>
            <linearGradient id="onboard-line" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0%" stopColor="rgba(143,183,255,0.12)" />
              <stop offset="50%" stopColor="rgba(143,183,255,0.58)" />
              <stop offset="100%" stopColor="rgba(231,191,120,0.56)" />
            </linearGradient>
          </defs>
          <path d="M160 68 C250 68 250 68 338 68" stroke="url(#onboard-line)" strokeWidth="2" strokeLinecap="round" />
          <path d="M430 68 C520 68 520 138 600 138" stroke="url(#onboard-line)" strokeWidth="2" strokeLinecap="round" />
          <path d="M430 68 C520 68 520 228 600 228" stroke="url(#onboard-line)" strokeWidth="2" strokeLinecap="round" />
        </svg>

        <div className="onboarding-trace absolute left-[118px] top-[58px] h-2.5 w-2.5 rounded-full" style={{ background: "var(--accent)" }} />
        <div className="onboarding-trace onboarding-trace-delay absolute left-[392px] top-[58px] h-2.5 w-2.5 rounded-full" style={{ background: "var(--warning)" }} />

        <div className="task-node onboarding-float absolute left-8 top-8 w-32 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--t3)" }}>task-001</span>
            <span className="status-dot h-2.5 w-2.5 rounded-full" style={{ background: "var(--success)" }} />
          </div>
          <p className="text-sm font-semibold" style={{ color: "var(--t1)" }}>Plan the system</p>
          <p className="status-complete mt-3 inline-flex rounded-md border px-2 py-1 text-[11px] font-semibold">
            completed
          </p>
        </div>

        <div className="task-node onboarding-float onboarding-delay-2 absolute left-[300px] top-8 w-32 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--t3)" }}>task-002</span>
            <span className="status-dot h-2.5 w-2.5 rounded-full" style={{ background: "var(--warning)" }} />
          </div>
          <p className="text-sm font-semibold" style={{ color: "var(--t1)" }}>Implement tasks</p>
          <p className="status-progress mt-3 inline-flex rounded-md border px-2 py-1 text-[11px] font-semibold">
            in_progress
          </p>
        </div>

        <div className="task-node onboarding-float onboarding-delay-3 absolute right-8 top-[78px] w-32 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--t3)" }}>task-003</span>
            <span className="status-dot h-2.5 w-2.5 rounded-full" style={{ background: "var(--t3)" }} />
          </div>
          <p className="text-sm font-semibold" style={{ color: "var(--t1)" }}>Review output</p>
          <p className="status-pending mt-3 inline-flex rounded-md border px-2 py-1 text-[11px] font-semibold">
            pending
          </p>
        </div>

        <div className="task-node onboarding-float onboarding-delay-4 absolute right-8 bottom-8 w-32 p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--t3)" }}>task-004</span>
            <span className="status-dot h-2.5 w-2.5 rounded-full" style={{ background: "var(--t3)" }} />
          </div>
          <p className="text-sm font-semibold" style={{ color: "var(--t1)" }}>Ship changes</p>
          <p className="status-pending mt-3 inline-flex rounded-md border px-2 py-1 text-[11px] font-semibold">
            pending
          </p>
        </div>
      </div>
    </div>
  );
}

export function OnboardingWizard({ lang, onFinish }: OnboardingWizardProps) {
  const copy = COPY[lang];
  const [step, setStep] = useState(0);
  const [workspaceName, setWorkspaceName] = useState("My First Project");
  const [workspacePath, setWorkspacePath] = useState("");
  const [copied, setCopied] = useState(false);

  const prompt = buildPlannerPrompt(workspaceName, workspacePath, lang);
  const previewPath = resolveMemoryFilePath(workspacePath);

  function handleCreate() {
    if (!workspaceName.trim()) {
      setWorkspaceName("My First Project");
    }
    setStep(2);
  }

  function handleCopy() {
    void navigator.clipboard.writeText(prompt);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  function finishWizard() {
    onFinish({
      name: workspaceName.trim() || "My First Project",
      path: workspacePath.trim(),
    });
  }

  return (
    <div className="app-frame bg-grid relative min-h-screen overflow-hidden">
      <div className="relative z-10 mx-auto flex min-h-screen max-w-7xl items-center px-6 py-10">
        <div className="grid w-full gap-8 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="control-surface flex flex-col justify-between p-8">
            <div>
              <div className="mb-6 inline-flex rounded-md border px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.18em]" style={{ borderColor: "var(--border-c)", background: "var(--accent-bg)", color: "var(--accent-strong)" }}>
                {copy.badge}
              </div>
              <div className="mb-8 flex items-center gap-3">
                {[
                  { index: 0, label: copy.stepOne },
                  { index: 1, label: copy.stepTwo },
                  { index: 2, label: copy.stepThree },
                ].map((item) => {
                  const active = step === item.index;
                  const done = step > item.index;

                  return (
                    <div key={item.index} className="flex items-center gap-3">
                      <div
                        className="flex h-9 w-9 items-center justify-center rounded-full border text-sm font-bold"
                        style={
                          active
                            ? { borderColor: "var(--accent)", background: "var(--accent-bg)", color: "var(--accent-strong)" }
                            : done
                              ? { borderColor: "var(--border-strong)", background: "var(--bg-card)", color: "var(--t2)" }
                              : { borderColor: "var(--border-c)", background: "var(--bg-muted)", color: "var(--t3)" }
                        }
                      >
                        {item.index + 1}
                      </div>
                      <span className="text-sm font-semibold" style={{ color: active ? "var(--t1)" : "var(--t3)" }}>{item.label}</span>
                    </div>
                  );
                })}
              </div>

              {step === 0 && (
                <div className="max-w-xl">
                  <h1 className="text-4xl font-semibold leading-tight tracking-tight lg:text-5xl" style={{ color: "var(--t1)" }}>{copy.title}</h1>
                  <p className="mt-5 text-base leading-8" style={{ color: "var(--t2)" }}>{copy.subtitle}</p>
                </div>
              )}

              {step === 1 && (
                <div className="max-w-xl">
                  <h2 className="text-3xl font-semibold tracking-tight" style={{ color: "var(--t1)" }}>{copy.setupTitle}</h2>
                  <p className="mt-4 text-base leading-8" style={{ color: "var(--t2)" }}>{copy.setupBody}</p>

                  <div className="mt-8 space-y-5">
                    <label className="block">
                      <span className="mb-2 block text-sm font-semibold" style={{ color: "var(--t2)" }}>{copy.workspaceName}</span>
                      <input
                        value={workspaceName}
                        onChange={(event) => setWorkspaceName(event.target.value)}
                        className="field-input w-full rounded-lg px-4 py-3 text-sm outline-none"
                        placeholder="My First Project"
                      />
                    </label>

                    <label className="block">
                      <span className="mb-2 block text-sm font-semibold" style={{ color: "var(--t2)" }}>{copy.workspacePath}</span>
                      <input
                        value={workspacePath}
                        onChange={(event) => setWorkspacePath(event.target.value)}
                        className="field-input w-full rounded-lg px-4 py-3 text-sm outline-none"
                        placeholder="D:\Projects\my-project\workspace"
                      />
                    </label>
                  </div>

                  <p className="mt-4 text-sm leading-7" style={{ color: "var(--t3)" }}>{copy.optionalHint}</p>

                  <div className="metric-card mt-8 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--t3)" }}>{copy.pathPreview}</p>
                    <p className="mt-2 break-all font-mono text-sm" style={{ color: "var(--accent-strong)" }}>{previewPath}</p>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="max-w-xl">
                  <h2 className="text-3xl font-semibold tracking-tight" style={{ color: "var(--t1)" }}>{copy.promptTitle}</h2>
                  <p className="mt-4 text-base leading-8" style={{ color: "var(--t2)" }}>{copy.promptBody}</p>

                  <div className="metric-card mt-7 p-5">
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--t3)" }}>Planner Prompt</p>
                      <button
                        type="button"
                        onClick={handleCopy}
                        className="primary-button rounded-lg px-3 py-2 text-xs font-semibold"
                      >
                        {copied ? copy.copied : copy.copy}
                      </button>
                    </div>
                    <pre className="max-h-[330px] overflow-auto whitespace-pre-wrap break-words text-sm leading-7" style={{ color: "var(--t2)" }}>
                      {prompt}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-10 flex flex-wrap items-center gap-3">
              {step > 0 && (
                <button
                  type="button"
                  onClick={() => setStep((current) => current - 1)}
                  className="quiet-button rounded-lg px-5 py-3 text-sm font-semibold"
                >
                  {copy.back}
                </button>
              )}

              {step === 0 && (
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="primary-button rounded-lg px-6 py-3 text-sm font-semibold"
                >
                  {copy.start}
                </button>
              )}

              {step === 1 && (
                <button
                  type="button"
                  onClick={handleCreate}
                  className="primary-button rounded-lg px-6 py-3 text-sm font-semibold"
                >
                  {copy.create}
                </button>
              )}

              {step === 2 && (
                <button
                  type="button"
                  onClick={finishWizard}
                  className="primary-button rounded-lg px-6 py-3 text-sm font-semibold"
                >
                  {copy.finish}
                </button>
              )}
            </div>
          </section>

          <section className="flex flex-col gap-6">
            <div>
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--t3)" }}>{copy.previewTitle}</p>
              <DemoDagCard />
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="metric-card p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--accent-strong)" }}>Plan</p>
                <p className="mt-3 text-sm leading-7" style={{ color: "var(--t2)" }}>{copy.planCard}</p>
              </div>
              <div className="metric-card p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--warning)" }}>Track</p>
                <p className="mt-3 text-sm leading-7" style={{ color: "var(--t2)" }}>{copy.trackCard}</p>
              </div>
              <div className="metric-card p-5">
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--success)" }}>Review</p>
                <p className="mt-3 text-sm leading-7" style={{ color: "var(--t2)" }}>{copy.reviewCard}</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
