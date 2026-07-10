import { useState } from "react";
import type { TranslationMessages } from "../../types";
import { Button, Surface } from "../ui/primitives";

type SettingsAiGuidePanelProps = {
  readonly t: TranslationMessages;
};

function copyText(text: string) {
  void navigator.clipboard.writeText(text);
}

export function SettingsAiGuidePanel({ t }: SettingsAiGuidePanelProps) {
  const [openTip, setOpenTip] = useState<number | null>(null);

  return (
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
  );
}
