import { useState, type Dispatch, type SetStateAction } from "react";
import type { Lang, SettingsTabId, ThemeId, TranslationMessages, Workspace } from "../types";
import { MetricTile, Surface, Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/primitives";
import { Settings, FileText, Sparkles } from "./ui/icons";
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
  readonly icon: React.ReactNode;
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
    { id: "general", label: t.generalSettingsTab, icon: <Settings className="h-4 w-4" /> },
    { id: "docs", label: t.usageGuideTab, icon: <FileText className="h-4 w-4" /> },
    { id: "guide", label: t.aiGuideTab, icon: <Sparkles className="h-4 w-4" /> },
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

      <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as SettingsTabId)} className="w-full">
        <TabsList className="mb-7 flex h-auto w-fit flex-wrap gap-1 p-1">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className="flex items-center gap-2 px-4 py-2 text-xs font-medium"
            >
              {tab.icon}
              <span>{tab.label}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="general" className="mt-0 outline-none">
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
        </TabsContent>
        <TabsContent value="docs" className="mt-0 outline-none">
          <SettingsDocsPanel t={t} />
        </TabsContent>
        <TabsContent value="guide" className="mt-0 outline-none">
          <SettingsAiGuidePanel t={t} />
        </TabsContent>
      </Tabs>
    </Surface>
  );
}
