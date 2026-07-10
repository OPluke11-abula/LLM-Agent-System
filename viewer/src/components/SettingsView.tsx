import { useState, type Dispatch, type SetStateAction } from "react";
import type { Lang, SettingsTabId, ThemeId, TranslationMessages, Workspace } from "../types";
import { Button, MetricTile, Surface } from "./ui/primitives";
import { SettingsAiGuidePanel } from "./settings/SettingsAiGuidePanel";
import { SettingsDocsPanel } from "./settings/SettingsDocsPanel";
import { SettingsGeneralPanel } from "./settings/SettingsGeneralPanel";

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

type SettingsTab = {
  readonly id: SettingsTabId;
  readonly label: string;
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
  const [activeTab, setActiveTab] = useState<SettingsTabId>("general");
  const tabs: readonly SettingsTab[] = [
    { id: "general", label: t.generalSettingsTab },
    { id: "docs", label: t.usageGuideTab },
    { id: "guide", label: t.aiGuideTab },
  ];
  const configuredWorkspaceCount = workspaces.filter((workspace) => workspace.path.trim()).length;

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
          <MetricTile
            label={t.settingsMetricPaths}
            value={configuredWorkspaceCount}
            tone={configuredWorkspaceCount ? "success" : "warning"}
          />
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
        <SettingsGeneralPanel
          lang={lang}
          setLang={setLang}
          theme={theme}
          setTheme={setTheme}
          workspaces={workspaces}
          setWorkspaces={setWorkspaces}
          t={t}
          relaunchOnboarding={relaunchOnboarding}
        />
      )}
      {activeTab === "docs" && <SettingsDocsPanel t={t} />}
      {activeTab === "guide" && <SettingsAiGuidePanel t={t} />}
    </Surface>
  );
}
