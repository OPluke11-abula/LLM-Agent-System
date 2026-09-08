import type { Dispatch, SetStateAction } from "react";
import { ALL_SKILLS, CAT_KEYS } from "../constants";
import { Card, CardContent, CardHeader, CardTitle, MetricTile, StatusBadge, Surface, Switch } from "./ui/primitives";
import { Boxes, Cpu } from "./ui/icons";
import type { Lang, TranslationMessages } from "../types";

type ModsViewProps = {
  t: TranslationMessages;
  lang: Lang;
  agentsEnabled: boolean;
  setAgentsEnabled: Dispatch<SetStateAction<boolean>>;
  activeSkills: Record<string, boolean>;
  setActiveSkills: Dispatch<SetStateAction<Record<string, boolean>>>;
};

export function ModsView({
  t,
  lang,
  agentsEnabled,
  setAgentsEnabled,
  activeSkills,
  setActiveSkills,
}: ModsViewProps) {
  const categoryLabels = {
    backend: t.catBackend,
    mobile: t.catMobile,
    testing: t.catTesting,
    quality: t.catQuality,
  };
  const enabledCount = Object.values(activeSkills).filter(Boolean).length;

  return (
    <Surface elevated className="h-full overflow-y-auto p-6">
      <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">
            <Boxes className="h-3.5 w-3.5" />
            <span>{t.modsIntroLabel}</span>
          </p>
          <h2 className="mt-1 text-xl font-bold t1">{t.mods}</h2>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed t3">{t.modsIntroBody}</p>
        </div>
        <StatusBadge tone={agentsEnabled ? "success" : "warning"}>
          {agentsEnabled ? t.writebackOnBadge : t.writebackOffBadge}
        </StatusBadge>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricTile label={t.modsMetricSkills} value={ALL_SKILLS.length} />
        <MetricTile label={t.modsMetricEnabled} value={enabledCount} tone={enabledCount > 0 ? "success" : "neutral"} />
        <MetricTile label={t.modsMetricCategories} value={CAT_KEYS.length} tone="accent" />
        <MetricTile
          label={t.agentsMdMetricLabel}
          value={agentsEnabled ? t.onState : t.offState}
          tone={agentsEnabled ? "success" : "warning"}
        />
      </div>

      <Card className="mb-6 p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-bold t1">{t.agentsMdToggle}</p>
            <p className="mt-0.5 text-xs t3">{t.agentsMdDesc}</p>
          </div>
          <Switch
            aria-label={t.agentsMdToggle}
            checked={agentsEnabled}
            onCheckedChange={(checked) => setAgentsEnabled(checked)}
          />
        </div>
      </Card>

      <p className="mb-1 text-[10px] font-bold uppercase tracking-widest t3">{t.skillsTitle}</p>
      <p className="mb-5 text-xs t3">{t.skillsDesc}</p>
      <div className="grid gap-4 xl:grid-cols-2">
        {CAT_KEYS.map((category) => {
          const categorySkills = ALL_SKILLS.filter((skill) => skill.cat === category);
          const activeCount = categorySkills.filter((skill) => activeSkills[skill.id]).length;
          return (
            <Card key={category}>
              <CardHeader className="p-4 pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-[var(--accent)]" />
                    <CardTitle className="text-xs uppercase tracking-widest t3">
                      {categoryLabels[category]}
                    </CardTitle>
                  </div>
                  <StatusBadge tone="neutral">
                    {activeCount}/{categorySkills.length}
                  </StatusBadge>
                </div>
              </CardHeader>
              <CardContent className="p-4 pt-2">
                <div className="grid gap-2">
                  {categorySkills.map((skill, index) => {
                    const isActive = Boolean(activeSkills[skill.id]);
                    return (
                      <div
                        key={skill.id}
                        className="group flex items-center justify-between gap-3 rounded-lg border px-3.5 py-2.5 transition-colors"
                        style={{
                          background: isActive ? "var(--accent-bg)" : "var(--bg-panel)",
                          borderColor: isActive ? "var(--accent)" : "var(--border-c)",
                        }}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[9px] t3">
                              {category.slice(0, 2).toUpperCase()}-{String(index + 1).padStart(2, "0")}
                            </span>
                            {isActive && <StatusBadge tone="success">{t.activeBadge}</StatusBadge>}
                          </div>
                          <span className="mt-0.5 block text-xs font-medium leading-snug t1">
                            {lang === "zh" ? skill.zh : skill.en}
                          </span>
                        </div>
                        <Switch
                          aria-label={lang === "zh" ? skill.zh : skill.en}
                          checked={isActive}
                          onCheckedChange={(checked) =>
                            setActiveSkills((current) => ({
                              ...current,
                              [skill.id]: checked,
                            }))
                          }
                        />
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </Surface>
  );
}
