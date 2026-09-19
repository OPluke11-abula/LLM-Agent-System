import React, { useState } from "react";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Surface } from "../ui/primitives";
import { Folder, Plus, Sparkles, Trash2 } from "../ui/icons";
import { ALL_LANGS } from "../../constants";
import type { TranslationMessages, Workspace } from "../../types";

export type WorkspaceField = "name" | "lang" | "path";

interface WorkspacesConfigCardProps {
  t: TranslationMessages;
  workspaces: readonly Workspace[];
  onAddWorkspace: () => void;
  onRemoveWorkspace: (id: string) => void;
  onUpdateWorkspace: (id: string, field: WorkspaceField, value: string) => void;
}

export const WorkspacesConfigCard: React.FC<WorkspacesConfigCardProps> = ({
  t,
  workspaces,
  onAddWorkspace,
  onRemoveWorkspace,
  onUpdateWorkspace,
}) => {
  const [draftPaths, setDraftPaths] = useState<Record<string, string>>({});

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Folder className="h-4 w-4 text-[var(--accent)]" />
            <CardTitle>{t.workspaces}</CardTitle>
          </div>
          <Button type="button" onClick={onAddWorkspace} variant="primary" className="flex items-center gap-1.5 px-3 py-1.5 text-xs">
            <Plus className="h-3.5 w-3.5" />
            <span>{t.addWorkspace}</span>
          </Button>
        </div>
        <CardDescription>管理參與 Swarm 運作的多個專案工作區路徑與技術棧</CardDescription>
      </CardHeader>
      <CardContent>
        <Surface className="mb-4 flex items-start gap-3 rounded-lg border p-3" style={{ borderColor: "var(--border-c)" }}>
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent)]" />
          <div>
            <p className="text-xs font-bold" style={{ color: "var(--accent)" }}>
              {t.aiHowTitle}
            </p>
            <p className="mt-1 text-xs leading-relaxed t2">{t.aiHowBody}</p>
          </div>
        </Surface>

        <div className="space-y-3">
          {workspaces.map((workspace) => (
            <Surface key={workspace.id} className="space-y-2.5 rounded-lg border p-3.5" style={{ borderColor: "var(--border-c)", background: "var(--bg-card)" }}>
              <div className="flex items-center gap-2.5">
                <Input
                  aria-label={`${t.wsName}: ${workspace.name}`}
                  value={workspace.name}
                  onChange={(event) => onUpdateWorkspace(workspace.id, "name", event.target.value)}
                  placeholder={t.wsName}
                  className="min-w-0 flex-1"
                />
                <select
                  aria-label={`${workspace.name} language`}
                  value={workspace.lang}
                  onChange={(event) => onUpdateWorkspace(workspace.id, "lang", event.target.value)}
                  className="flex h-9 rounded-lg border bg-[var(--bg-card)] px-2 py-1.5 text-xs t1 shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                  style={{ borderColor: "var(--border-c)" }}
                >
                  {ALL_LANGS.map((item) => (
                    <option key={item}>{item}</option>
                  ))}
                </select>
                {workspaces.length > 1 && (
                  <Button
                    type="button"
                    onClick={() => onRemoveWorkspace(workspace.id)}
                    variant="danger"
                    className="flex h-9 shrink-0 items-center justify-center px-2.5"
                    title={t.removeWs}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
                <Input
                  aria-label={`${workspace.name} ${t.wsPathPlaceholder}`}
                  value={draftPaths[workspace.id] ?? workspace.path}
                  onChange={(event) =>
                    setDraftPaths((current) => ({
                      ...current,
                      [workspace.id]: event.target.value,
                    }))
                  }
                  placeholder={t.wsPathPlaceholder}
                  className="font-mono"
                />
                <Button
                  type="button"
                  onClick={() =>
                    draftPaths[workspace.id] !== undefined &&
                    onUpdateWorkspace(workspace.id, "path", draftPaths[workspace.id])
                  }
                  variant="primary"
                  className="px-3 py-1.5 text-xs font-semibold"
                  disabled={draftPaths[workspace.id] === undefined || draftPaths[workspace.id] === workspace.path}
                >
                  {t.confirm}
                </Button>
              </div>
            </Surface>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
