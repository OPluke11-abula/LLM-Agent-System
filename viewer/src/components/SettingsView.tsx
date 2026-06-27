import { useState, useEffect, type Dispatch, type SetStateAction } from "react";
import { ALL_LANGS, THEME_LIST } from "../constants";
import type { Lang, SettingsTabId, ThemeId, TranslationMessages, Workspace, LlmConfig, LlmConfigPayload } from "../types";
import { logUiDiagnostic } from "../utils/logger";
import { Button, MetricTile, StatusBadge, Surface } from "./ui/primitives";

type SettingsViewProps = {
  lang: Lang;
  setLang: (lang: Lang) => void;
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  workspaces: Workspace[];
  setWorkspaces: Dispatch<SetStateAction<Workspace[]>>;
  t: TranslationMessages;
  relaunchOnboarding: () => void;
};

export function SettingsView({
  lang,
  setLang,
  theme,
  setTheme,
  workspaces,
  setWorkspaces,
  t,
  relaunchOnboarding,
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
      .catch((err) => {
        setSaveStatus("Failed to load LLM config");
        logUiDiagnostic("Failed to load config", err);
      });
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
      } else {
        setSaveStatus(`Failed to save config (${res.status})`);
      }
    } catch (err) {
      setSaveStatus("Failed to save LLM config");
      logUiDiagnostic("Failed to save config", err);
    }
  }

  const tabs: Array<{ id: SettingsTabId; label: string }> = [
    { id: "general", label: t.generalSettingsTab },
    { id: "docs", label: t.usageGuideTab },
    { id: "guide", label: t.aiGuideTab },
  ];

  const configuredWorkspaceCount = workspaces.filter((workspace) => workspace.path.trim()).length;

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
    <Surface elevated className="h-full overflow-y-auto p-6">
      <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] t3">{t.settingsIntroLabel}</p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight t1">{t.settingsTitle}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed t2">{t.settingsIntroBody}</p>
        </div>
        <div className="grid min-w-[280px] grid-cols-3 gap-2">
          <MetricTile label={t.settingsMetricTabs} value={tabs.length} />
          <MetricTile label={t.settingsMetricWorkspaces} value={workspaces.length} tone="accent" />
          <MetricTile label={t.settingsMetricPaths} value={configuredWorkspaceCount} tone={configuredWorkspaceCount ? "success" : "warning"} />
        </div>
      </div>

      <div className="mb-7 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            variant={activeTab === tab.id ? "primary" : "quiet"}
            className="px-4 py-2 text-sm"
          >
            {tab.label}
          </Button>
        ))}
      </div>

      {activeTab === "general" && (
        <>
          <Surface as="section" className="mb-7 p-5">
            <label className="mb-3 block text-[10px] font-bold uppercase tracking-widest t3">{t.langLabel}</label>
            <div className="flex flex-wrap gap-3">
              {(["zh", "en", "ja", "fr"] as Lang[]).map((item) => {
                const langNames: Record<Lang, string> = {
                  zh: "繁體中文",
                  en: "English",
                  ja: "日本語",
                  fr: "Français",
                };
                return (
                  <Button
                    key={item}
                    type="button"
                    onClick={() => setLang(item)}
                    variant={lang === item ? "primary" : "quiet"}
                    className="px-5 py-2 text-sm"
                  >
                    {langNames[item]}
                  </Button>
                );
              })}
            </div>
          </Surface>

          <Surface as="section" className="mb-7 p-5">
            <label className="mb-3 block text-[10px] font-bold uppercase tracking-widest t3">{t.relaunchTutorialBtn}</label>
            <div>
              <Button
                type="button"
                onClick={relaunchOnboarding}
                variant="primary"
                className="px-5 py-2.5 text-sm"
              >
                {t.relaunchTutorialBtn}
              </Button>
            </div>
          </Surface>

          <Surface as="section" className="mb-7 p-5">
            <label className="mb-3 block text-[10px] font-bold uppercase tracking-widest t3">{t.themeLabel}</label>
            <div className="flex flex-wrap gap-2">
              {THEME_LIST.map(({ id }) => (
                <Button
                  key={id}
                  type="button"
                  onClick={() => setTheme(id)}
                  variant={theme === id ? "primary" : "quiet"}
                  className="px-4 py-2"
                >
                  {t.themes[id]}
                </Button>
              ))}
            </div>
          </Surface>

          <Surface as="section" className="mb-7 p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <label className="block text-[10px] font-bold uppercase tracking-widest t3">{t.llmConfigTitle}</label>
              {llmConfig?.api_key_set && <StatusBadge tone="success">{t.envKeySetBadge}</StatusBadge>}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-bold t2">{t.llmProviderLabel}</label>
                <select
                  value={llmPayload.provider || ""}
                  onChange={(e) => setLlmPayload({ ...llmPayload, provider: e.target.value })}
                  className="field-input w-full rounded-lg px-3 py-2 text-sm"
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
                  className="field-input w-full rounded-lg px-3 py-2 text-sm"
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs font-bold t2">{t.llmApiKeyLabel}</label>
                <input
                  type="password"
                  value={llmPayload.api_key || ""}
                  onChange={(e) => setLlmPayload({ ...llmPayload, api_key: e.target.value })}
                  placeholder={llmConfig?.api_key_set ? "Current key is set. Leave blank to keep it." : "Enter API Key..."}
                  className="field-input w-full rounded-lg px-3 py-2 text-sm"
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
                    className="field-input w-full rounded-lg px-3 py-2 text-sm"
                  />
                </div>
              )}
            </div>
            <div className="mt-5 flex items-center gap-4">
              <Button
                type="button"
                onClick={saveLlmConfig}
                variant="primary"
                className="px-5 py-2 text-sm"
              >
                {t.saveConfigBtn}
              </Button>
              {saveStatus && <StatusBadge tone="success">{saveStatus}</StatusBadge>}
            </div>
          </Surface>

          <section className="mb-7">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[10px] font-bold uppercase tracking-widest t3">{t.workspaces}</p>
              <Button
                type="button"
                onClick={addWorkspace}
                variant="primary"
              >
                {t.addWorkspace}
              </Button>
            </div>
            <Surface className="mb-4 flex gap-3 p-4">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: "var(--accent)" }} />
              <div>
                <p className="text-xs font-bold" style={{ color: "var(--accent)" }}>
                  {t.aiHowTitle}
                </p>
                <p className="mt-1 text-xs leading-relaxed t2">{t.aiHowBody}</p>
              </div>
            </Surface>
            <div className="space-y-4">
              {workspaces.map((workspace) => (
                <Surface key={workspace.id} className="space-y-3 p-4">
                  <div className="flex items-center gap-3">
                    <input
                      value={workspace.name}
                      onChange={(event) => updateWorkspace(workspace.id, "name", event.target.value)}
                      placeholder={t.wsName}
                      className="field-input min-w-0 flex-1 rounded-lg px-3 py-2 text-sm"
                    />
                    <select
                      value={workspace.lang}
                      onChange={(event) => updateWorkspace(workspace.id, "lang", event.target.value)}
                      className="field-input rounded-lg px-2 py-2 text-sm"
                    >
                      {ALL_LANGS.map((item) => (
                        <option key={item}>{item}</option>
                      ))}
                    </select>
                    {workspaces.length > 1 && (
                      <Button
                        type="button"
                        onClick={() => removeWorkspace(workspace.id)}
                        variant="danger"
                        className="flex-shrink-0"
                      >
                        {t.removeWs}
                      </Button>
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
                      className="field-input w-full rounded-lg px-3 py-2 font-mono text-xs"
                    />
                    <Button
                      type="button"
                      onClick={() =>
                        draftPaths[workspace.id] !== undefined &&
                        updateWorkspace(workspace.id, "path", draftPaths[workspace.id])
                      }
                      variant="primary"
                      className="px-3 py-2"
                      disabled={draftPaths[workspace.id] === undefined || draftPaths[workspace.id] === workspace.path}
                    >
                      {t.confirm}
                    </Button>
                  </div>
                </Surface>
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
                <Surface key={`${step.title}-${index}`} className="flex gap-4 p-4">
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
                </Surface>
              ))}
            </div>
          </section>

          <section className="mb-4">
            <p className="mb-4 text-[10px] font-bold uppercase tracking-widest t3">{t.opManual}</p>
            <div className="grid gap-3">
              {t.opSteps.map((step, index) => (
                <Surface key={`${step.title}-${index}`} className="flex gap-4 p-4">
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
                </Surface>
              ))}
            </div>
          </section>
        </>
      )}

      {activeTab === "guide" && (
        <>
          <section className="mb-7">
            <Surface className="mb-4 flex gap-3 p-4">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: "var(--accent)" }} />
              <p className="text-sm font-bold" style={{ color: "var(--accent)" }}>
                {t.aiGuideTitle}
              </p>
            </Surface>
            <div className="grid gap-3">
              {t.aiGuideSteps.map((step, index) => (
                <Surface key={`${step.title}-${index}`} className="p-4">
                  <div className="mb-2 flex items-start justify-between gap-3">
                    <p
                      className="text-sm font-bold t1"
                      style={index === t.aiGuideSteps.length - 1 ? { color: "var(--accent)" } : undefined}
                    >
                      {step.title}
                    </p>
                    <Button
                      type="button"
                      onClick={() => copyText(step.body)}
                      variant="primary"
                      className="px-2 py-1"
                      title={t.copy}
                    >
                      {t.copy}
                    </Button>
                  </div>
                  <p className="text-xs leading-relaxed t3" style={{ whiteSpace: "pre-wrap" }}>
                    {step.body}
                  </p>
                </Surface>
              ))}
            </div>
          </section>

          <section className="mb-4">
            <p className="mb-1 text-[10px] font-bold uppercase tracking-widest t3">{t.aiTipsTitle}</p>
            <p className="mb-4 text-xs t3">{t.aiTipsDesc}</p>
            <div className="space-y-2">
              {t.tips.map((tip, index) => (
                <Surface key={`${tip.title}-${index}`} className="overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setOpenTip(openTip === index ? null : index)}
                    className="flex w-full items-center justify-between px-5 py-3.5 text-left text-sm font-bold transition-colors t1 hover:bg-[var(--bg-muted)]"
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
                </Surface>
              ))}
            </div>
          </section>
        </>
      )}
    </Surface>
  );
}
