import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import type { MissionCreateRequest } from "../../generated/missionContracts";
import { MissionApiError, missionApi } from "../../services/missionApi";
import { Button } from "../ui/primitives";

export function MissionNewPage() {
  const navigate = useNavigate();
  const [requirement, setRequirement] = useState("");
  const [repositoryId, setRepositoryId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const payload: MissionCreateRequest = { requirement, repository_id: repositoryId };
    try {
      const mission = await missionApi.create(payload);
      navigate(`/missions/${encodeURIComponent(mission.mission_id)}`);
    } catch (cause: unknown) {
      setError(cause instanceof MissionApiError ? cause.message : "Mission could not be created");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="mx-auto flex h-full min-h-0 max-w-3xl flex-col gap-5 overflow-auto pb-6">
      <header><p className="eyebrow-label">Mission intake</p><h1 className="mt-2 text-2xl font-semibold t1">New mission</h1><p className="mt-2 text-sm t2">Define the durable requirement and repository scope. Execution remains gated by the backend state machine.</p></header>
      <form className="control-surface grid gap-5 p-5" onSubmit={submit}>
        <label className="grid gap-2 text-sm font-semibold t1">Requirement<textarea required minLength={1} maxLength={4000} value={requirement} onChange={(event) => setRequirement(event.target.value)} className="min-h-32 rounded-lg border bg-[var(--bg-muted)] p-3 text-sm font-normal t1 outline-none focus:ring-2" style={{ borderColor: "var(--border-c)", outlineColor: "var(--accent)" }} placeholder="What should the agent control plane accomplish?" /></label>
        <label className="grid gap-2 text-sm font-semibold t1">Repository ID<input required value={repositoryId} onChange={(event) => setRepositoryId(event.target.value)} className="rounded-lg border bg-[var(--bg-muted)] px-3 py-2.5 text-sm font-normal t1 outline-none focus:ring-2" style={{ borderColor: "var(--border-c)", outlineColor: "var(--accent)" }} placeholder="owner/repository" /></label>
        {error && <p className="text-sm" style={{ color: "var(--danger)" }} role="alert">{error}</p>}
        <div className="flex flex-wrap items-center justify-end gap-3 border-t pt-4" style={{ borderColor: "var(--border-c)" }}><Button type="button" onClick={() => navigate("/missions")}>Cancel</Button><Button type="submit" variant="primary" disabled={submitting}>{submitting ? "Creating…" : "Create mission"}</Button></div>
      </form>
    </section>
  );
}
