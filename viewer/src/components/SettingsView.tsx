import { useState, useEffect, type Dispatch, type SetStateAction } from "react";
import { ALL_LANGS, THEME_LIST } from "../constants";
import type { Lang, SettingsTabId, ThemeId, TranslationMessages, Workspace, LlmConfig, LlmConfigPayload } from "../types";

type SettingsViewProps = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  workspaces: Workspace[];
  setWorkspaces: Dispatch<SetStateAction<Workspace[]>>;
  t: TranslationMessages;
};

export function SettingsView({
  lang,
  setLang,
  theme,
  setTheme,
  workspaces,
  setWorkspaces,
  t,
}: SettingsViewProps) {
  const [openTip, setOpenTip] = useState<number | null>(null);
  const [draftPaths, setDraftPaths] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<SettingsTabId>("general");
  
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(null);
  const [llmPayload, setLlmPayload] = useState<LlmConfigPayload>({});
  const [saveStatus, setSaveStatus] = useState<string>("");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/v1/config")
      .then((res) => res.json())
      .then((data) => {
        setLlmConfig(data as LlmConfig);
        setLlmPayload({
          provider: data.provider,
          model: data.model,
          base_url: data.base_url,
          api_key: "",
        });
      })
      .catch((err) => console.error("Failed to load config:", err));
  }, []);

  async function saveLlmConfig() {
    try {
      const res = await fetch("http://127.0.0.1:8000/v1/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(llmPayload),
      });
      if (res.ok) {
        setSaveStatus(t.configSavedToast);
        setTimeout(() => setSaveStatus(""), 3000);
      }
    } catch (err) {
      console.error("Failed to save config:", err);
    }
  }

  const inputStyle = {
    background: "var(--bg-card)",
    borderColor: "var(--border-c)",
    color: "var(--t1)",
  };

  const tabs: Array<{ id: SettingsTabId; label: string }> = [
    { id: "general", label: `⚙️ ${t.generalSettingsTab}` },
    { id: "docs", label: `📖 ${t.usageGuideTab}` },
    { id: "guide", label: `🤝 ${t.aiGuideTab}` },
  ];

  function addWorkspace() {
    setWorkspaces((current) => [
      ...current,
      {
        id: `ws-${Date.now()}`,
        name: `Project ${current.length + 1}`,
        lang: "TypeScript",
        path: "",
      },
    ]);
  }

  function removeWorkspace(id: string) {
    setWorkspaces((current) => current.filter((workspace) => workspace.id !== id));
  }

  function updateWorkspace(id: string, field: "name" | "lang" | "path", value: string) {
    setWorkspaces((current) =>
      current.map((workspace) => (workspace.id === id ? { ...workspace, [field]: value } : workspace)),
    );
  }

  function copyText(text: string) {
    void navigator.clipboard.writeText(text);
  }

  return (
    <div className="h-full overflow-y-auto rounded-2xl border p-6 shadow-xl panel-bg">
      <h2 className="mb-6 text-xl font-bold t1">{t.settingsTitle}</h2>

      <div className="mb-7 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className="rounded-lg border px-4 py-2 text-sm font-bold transition-all"
            style={
              activeTab === tab.id
                ? { background: "var(--accent-bg)", borderColor: "var(--accent)", color: "var(--accent)" }
                : inputStyle
            }
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "general" && (
        <>
          <section className="card-bg mb-7 rounded-xl border p-5">
            <label className="mb-3 block text-[10px] font-bold uppercase tracking-widest t3">{t.langLabel}</label>
            <div className="flex gap-3">
              {(["zh", "en"] as Lang[]).map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setLang(item)}
                  className="rounded-lg border px-5 py-2 text-sm font-bold transition-all"
                  style={
                    lang === item
                      ? { background: "var(--accent-bg)", borderColor: "var(--accent)", color: "var(--accent)" }
                      : inputStyle
                  }
                >
                  {item === "zh" ? "中文" : "English"}
                </button>
              ))}
            </div>
          </section>

          <section className="card-bg mb-7 rounded-xl border p-5">
            <label className="mb-3 block text-[10px] font-bold uppercase tracking-widest t3">{t.themeLabel}</label>
            <div className="flex flex-wrap gap-2">
              {THEME_LIST.map(({ id }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => setTheme(id)}
                  className="rounded-lg border px-4 py-2 text-xs font-bold transition-all"
                  style={
                    theme === id
                      ? { background: "var(--accent-bg)", borderColor: "var(--accent)", color: "var(--accent)" }
                      : inputStyle
                  }
                >
                  {t.themes[id]}
                </button>
              ))}
            </div>
          </section>

          <section className="card-bg mb-7 rounded-xl border p-5">
            <label className="mb-3 block text-[10px] font-bold uppercase tracking-widest t3">{t.llmConfigTitle}</label>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-bold t2">{t.llmProviderLabel}</label>
                <select
                  value={llmPayload.provider || ""}
                  onChange={(e) => setLlmPayload({ ...llmPayload, provider: e.target.value })}
                  className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  style={inputStyle}
                >
                  <option value="google-genai">Google GenAI (Gemini)</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="ollama">Ollama (Local)</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-bold t2">{t.llmModelLabel}</label>
                <input
                  type="text"
                  value={llmPayload.model || ""}
                  onChange={(e) => setLlmPayload({ ...llmPayload, model: e.target.value })}
                  placeholder="e.g. gemini-2.5-flash"
                  className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  style={inputStyle}
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-bold t2">
                  {t.llmApiKeyLabel}
                  {llmConfig?.api_key_set && (
                    <span className="ml-2 text-[10px] text-green-500 font-normal tracking-wide border border-green-500/30 px-1.5 py-0.5 rounded">
                      ✓ SET IN .ENV
                    </span>
                  )}
                </label>
                <input
                  type="password"
                  value={llmPayload.api_key || ""}
                  onChange={(e) => setLlmPayload({ ...llmPayload, api_key: e.target.value })}
                  placeholder={llmConfig?.api_key_set ? "•••••••••••••••••••• (Leave blank to keep current)" : "Enter API Key..."}
                  className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1"
                  style={inputStyle}
                />
              </div>
              {(llmPayload.provider === "ollama" || llmPayload.provider === "openai") && (
                <div className="md:col-span-2">
                  <label className="mb-1 block text-xs font-bold t2">{t.llmBaseUrlLabel}</label>
                  <input
                    type="text"
                    value={llmPayload.base_url || ""}
                    onChange={(e) => setLlmPayload({ ...llmPayload, base_url: e.target.value })}
                    placeholder="e.g. http://127.0.0.1:11434"
                    className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1"
                    style={inputStyle}
                  />
                </div>
              )}
            </div>
            <div className="mt-5 flex items-center gap-4">
              <button
                type="button"
                onClick={saveLlmConfig}
                className="rounded-lg border px-5 py-2 text-sm font-bold transition-all hover:brightness-110"
                style={{ background: "var(--accent)", borderColor: "var(--accent)", color: "#fff" }}
              >
                {t.saveConfigBtn}
              </button>
              {saveStatus && <span className="text-sm font-bold" style={{ color: "var(--accent)" }}>{saveStatus}</span>}
            </div>
          </section>

          <section className="mb-7">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[10px] font-bold uppercase tracking-widest t3">{t.workspaces}</p>
              <button
                type="button"
                onClick={addWorkspace}
                className="rounded-lg border px-3 py-1.5 text-xs font-bold transition-colors"
                style={{ color: "var(--accent)", borderColor: "var(--accent)", background: "var(--accent-bg)" }}
              >
                {t.addWorkspace}
              </button>
            </div>
            <div
              className="mb-4 flex gap-3 rounded-xl border p-4"
              style={{ background: "var(--accent-bg)", borderColor: "var(--accent)" }}
            >
              <span style={{ color: "var(--accent)" }}>💡</span>
              <div>
                <p className="text-xs font-bold" style={{ color: "var(--accent)" }}>
                  {t.aiHowTitle}
                </p>
                <p className="mt-1 text-xs leading-relaxed t2">{t.aiHowBody}</p>
              </div>
            </div>
            <div className="space-y-4">
              {workspaces.map((workspace) => (
                <div key={workspace.id} className="card-bg space-y-3 rounded-xl border p-4">
                  <div className="flex items-center gap-3">
                    <input
                      value={workspace.name}
                      onChange={(event) => updateWorkspace(workspace.id, "name", event.target.value)}
                      placeholder={t.wsName}
                      className="min-w-0 flex-1 rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-1"
                      style={inputStyle}
                    />
                    <select
                      value={workspace.lang}
                      onChange={(event) => updateWorkspace(workspace.id, "lang", event.target.value)}
                      className="rounded-lg border px-2 py-2 text-sm focus:outline-none focus:ring-1"
                      style={inputStyle}
                    >
                      {ALL_LANGS.map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                    {workspaces.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeWorkspace(workspace.id)}
                        className="t3 flex-shrink-0 rounded-lg border px-2 py-1.5 text-xs font-bold transition-colors hover:text-red-400"
                        style={{ borderColor: "var(--border-c)" }}
                      >
                        {t.removeWs}
                      </button>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <input
                      value={draftPaths[workspace.id] ?? workspace.path}
                      onChange={(event) =>
                        setDraftPaths((current) => ({
                          ...current,
                          [workspace.id]: event.target.value,
                        }))
                      }
                      placeholder={t.wsPathPlaceholder}
                      className="w-full rounded-lg border px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1"
                      style={{ ...inputStyle, opacity: 0.85 }}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        draftPaths[workspace.id] !== undefined &&
                        updateWorkspace(workspace.id, "path", draftPaths[workspace.id])
                      }
                      className="rounded-lg border px-3 py-2 text-xs font-bold transition-all"
                      style={
                        draftPaths[workspace.id] !== undefined && draftPaths[workspace.id] !== workspace.path
                          ? { background: "var(--accent)", color: "#fff", borderColor: "var(--accent)" }
                          : { ...inputStyle, opacity: 0.5, cursor: "not-allowed" }
                      }
                      disabled={draftPaths[workspace.id] === undefined || draftPaths[workspace.id] === workspace.path}
                    >
                      {t.confirm}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {activeTab === "docs" && (
        <>
          <section className="mb-7">
            <p className="mb-4 text-[10px] font-bold uppercase tracking-widest t3">{t.howItWorks}</p>
            <div className="grid gap-3">
              {t.howSteps.map((step, index) => (
                <div key={`${step.title}-${index}`} className="card-bg flex gap-4 rounded-xl border p-4">
                  <div
                    className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-xs font-black text-white"
                    style={{ background: "var(--accent)", boxShadow: "0 4px 12px var(--accent-bg)" }}
                  >
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div>
                    <p className="text-sm font-bold t1">{step.title}</p>
                    <p className="mt-1 text-xs leading-relaxed t3">{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-4">
            <p className="mb-4 text-[10px] font-bold uppercase tracking-widest t3">{t.opManual}</p>
            <div className="grid gap-3">
              {t.opSteps.map((step, index) => (
                <div key={`${step.title}-${index}`} className="card-bg flex gap-4 rounded-xl border p-4">
                  <div
                    className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-xs font-black text-white"
                    style={{ background: "var(--t3)" }}
                  >
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div>
                    <p className="text-sm font-bold t1">{step.title}</p>
                    <p className="mt-1 text-xs leading-relaxed t3">{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {activeTab === "guide" && (
        <>
          <section className="mb-7">
            <div
              className="mb-4 flex gap-3 rounded-xl border p-4"
              style={{ background: "var(--accent-bg)", borderColor: "var(--accent)" }}
            >
              <span style={{ color: "var(--accent)" }}>🔰</span>
              <p className="text-sm font-bold" style={{ color: "var(--accent)" }}>
                {t.aiGuideTitle}
              </p>
            </div>
            <div className="grid gap-3">
              {t.aiGuideSteps.map((step, index) => (
                <div key={`${step.title}-${index}`} className="card-bg rounded-xl border p-4">
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <p
                      className="text-sm font-bold t1"
                      style={index === t.aiGuideSteps.length - 1 ? { color: "var(--accent)" } : undefined}
                    >
                      {step.title}
                    </p>
                    <button
                      type="button"
                      onClick={() => copyText(step.body)}
                      className="rounded border px-2 py-1 text-xs transition-opacity hover:opacity-100"
                      style={{ borderColor: "var(--accent)", color: "var(--accent)", opacity: 0.7 }}
                      title={t.copy}
                    >
                      {t.copy}
                    </button>
                  </div>
                  <p className="text-xs leading-relaxed t3" style={{ whiteSpace: "pre-wrap" }}>
                    {step.body}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="mb-4">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest t3">{t.aiTipsTitle}</p>
            <p className="mb-4 text-xs t3">{t.aiTipsDesc}</p>
            <div className="space-y-2">
              {t.tips.map((tip, index) => (
                <div key={`${tip.title}-${index}`} className="card-bg overflow-hidden rounded-xl border">
                  <button
                    type="button"
                    onClick={() => setOpenTip(openTip === index ? null : index)}
                    className="flex w-full items-center justify-between px-5 py-3.5 text-left text-sm font-bold transition-all hover:brightness-110 t1"
                  >
                    <span>{tip.title}</span>
                    <span
                      className={`ml-2 flex-shrink-0 text-xs transition-transform duration-300 t3 ${
                        openTip === index ? "rotate-180" : ""
                      }`}
                    >
                      ▾
                    </span>
                  </button>
                  {openTip === index && (
                    <div className="border-t px-5 pt-3 pb-4 text-xs leading-relaxed t2" style={{ borderColor: "var(--border-c)" }}>
                      {tip.body}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
