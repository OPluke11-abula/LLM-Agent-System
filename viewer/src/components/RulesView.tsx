import { useState, type Dispatch, type SetStateAction } from "react";
import { Modal } from "./Modal";
import { Button, Card, CardContent, MetricTile, StatusBadge, Surface } from "./ui/primitives";
import { Plus, ShieldCheck, Trash2 } from "./ui/icons";
import type { TranslationMessages } from "../types";

type RulesViewProps = {
  t: TranslationMessages;
  rules: string[];
  setRules: Dispatch<SetStateAction<string[]>>;
};

export function RulesView({ t, rules, setRules }: RulesViewProps) {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<number | null>(null);
  const [newRule, setNewRule] = useState("");

  function handleAddRule() {
    if (!newRule.trim()) {
      return;
    }

    setRules((current) => [...current, newRule.trim()]);
    setNewRule("");
    setAddModalOpen(false);
  }

  return (
    <Surface elevated className="flex h-full flex-col overflow-hidden p-6">
      <div className="mb-5 flex flex-shrink-0 flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--accent)]">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>{t.rulesIntroLabel}</span>
          </p>
          <h2 className="mt-1 text-xl font-bold t1">{t.aiRules}</h2>
          <p className="mt-1 max-w-2xl text-xs leading-relaxed t3">{t.rulesIntroBody}</p>
        </div>
        <Button
          type="button"
          onClick={() => setAddModalOpen(true)}
          variant="primary"
          className="flex items-center gap-1.5 self-start text-xs font-semibold md:self-auto"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>{t.addRule}</span>
        </Button>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricTile label={t.rulesMetricRules} value={rules.length} />
        <MetricTile label={t.rulesMetricScope} value={t.rulesMetricScopeValue} tone="accent" />
        <MetricTile label={t.rulesMetricWriteback} value={t.rulesMetricWritebackValue} tone="success" />
        <MetricTile label={t.rulesMetricReview} value={t.rulesMetricReviewValue} tone="warning" />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {rules.length === 0 ? (
          <Card className="flex min-h-[280px] flex-col items-center justify-center p-8 text-center">
            <ShieldCheck className="h-10 w-10 text-[var(--warning)]" />
            <StatusBadge tone="warning" className="mt-3">{t.noRulesBadge}</StatusBadge>
            <p className="mt-4 text-sm font-semibold t1">{t.noRulesTitle}</p>
            <p className="mt-1 max-w-sm text-xs leading-relaxed t3">{t.noRulesBody}</p>
            <Button type="button" variant="primary" onClick={() => setAddModalOpen(true)} className="mt-5 flex items-center gap-1.5">
              <Plus className="h-3.5 w-3.5" />
              <span>{t.addRule}</span>
            </Button>
          </Card>
        ) : (
          <div className="space-y-3">
            {rules.map((rule, index) => (
              <Card key={rule} className="transition-colors hover:border-[var(--accent)]">
                <CardContent className="flex items-start gap-3 p-4">
                  <div
                    className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md text-[10px] font-black"
                    style={{ background: "var(--accent-bg)", color: "var(--accent)" }}
                  >
                    {String(index + 1).padStart(2, "0")}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <StatusBadge tone="accent">{t.activeBadge}</StatusBadge>
                      <span className="font-mono text-[10px] t3">rule.{String(index + 1).padStart(2, "0")}</span>
                    </div>
                    <p className="text-xs leading-relaxed t1">{rule}</p>
                  </div>
                  <Button
                    type="button"
                    onClick={() => setDeleteTarget(index)}
                    variant="danger"
                    size="sm"
                    className="gap-1.5"
                    title={t.removeAction}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>{t.removeAction}</span>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {addModalOpen && (
        <Modal
          title={t.addRuleTitle}
          onConfirm={handleAddRule}
          onCancel={() => {
            setAddModalOpen(false);
            setNewRule("");
          }}
          confirmText={t.confirm}
          cancelText={t.cancel}
        >
          <textarea
            autoFocus
            value={newRule}
            onChange={(event) => setNewRule(event.target.value)}
            placeholder={t.addRulePlaceholder}
            rows={4}
            className="field-input w-full resize-none rounded-xl p-3 font-mono text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                handleAddRule();
              }
            }}
          />
        </Modal>
      )}

      {deleteTarget !== null && (
        <Modal
          title={t.deleteRuleTitle}
          onConfirm={() => {
            setRules((current) => current.filter((_, index) => index !== deleteTarget));
            setDeleteTarget(null);
          }}
          onCancel={() => setDeleteTarget(null)}
          confirmText={t.confirm}
          cancelText={t.cancel}
          danger
        >
          <p className="text-sm t2">{t.deleteRuleConfirm}</p>
          <Surface className="mt-3 rounded-lg border p-3 font-mono text-xs t2" style={{ borderColor: "var(--border-c)", background: "var(--bg-muted)" }}>
            {rules[deleteTarget]}
          </Surface>
        </Modal>
      )}
    </Surface>
  );
}
