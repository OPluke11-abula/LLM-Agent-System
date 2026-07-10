import type { TranslationMessages } from "../../types";
import { Surface } from "../ui/primitives";

type SettingsDocsPanelProps = {
  readonly t: TranslationMessages;
};

export function SettingsDocsPanel({ t }: SettingsDocsPanelProps) {
  return (
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
  );
}
