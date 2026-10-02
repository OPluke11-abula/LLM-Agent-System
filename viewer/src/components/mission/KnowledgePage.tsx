import { LinkButton, Surface } from "../ui/primitives";

export function KnowledgePage() {
  return <section className="flex h-full min-h-0 flex-col gap-5 overflow-auto pb-6"><header><p className="eyebrow-label">Knowledge surface</p><h1 className="mt-2 text-2xl font-semibold t1">Knowledge</h1><p className="mt-2 max-w-2xl text-sm t2">A reserved, truthful workspace for durable knowledge records.</p></header><Surface elevated className="p-8 text-center"><p className="text-lg font-semibold t1">No knowledge records connected</p><p className="mx-auto mt-2 max-w-lg text-sm t2">The current product contract exposes Mission records, evidence, and review history. Knowledge ingestion is not silently simulated.</p><LinkButton to="/missions" className="mt-5 inline-flex">Return to Missions</LinkButton></Surface></section>;
}
