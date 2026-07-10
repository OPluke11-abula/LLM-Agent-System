# Evidence Memory Bridge Workflow

## Purpose

Connect compact knowledge-base summaries to LAS's explicit evidence-memory
artifacts without duplicating raw output, enabling background capture, or
storing long-term memory by default.

## Boundary

- Raw, redacted command or tool output begins in [[evidence-capture]].
- The optional canonical memory pack lives under `.agent/memory/`: a copied raw
  evidence ref, an L1 atom, L2 scenario, optional L3 persona, Mermaid canvas,
  and `evidence-memory.json`.
- Knowledge-base notes, reports, and handoffs retain only a compact summary
  plus paths, hashes, and claim-to-evidence citations.
- This workflow is manual and command-driven. It does not create watchers,
  semantic retrieval, hooks, or automatic long-term-memory writes.

## When To Use

Use this bridge when evidence will support a durable decision, handoff, report,
or recurring workflow and the raw output is too large or volatile to copy into
the knowledge base.

## Procedure

1. Capture redacted, bounded raw output under
   `.agent/knowledge_base/evidence/YYYY-MM-DD-<topic>.md` using
   [[evidence-capture]].
2. If the evidence needs durable LAS traceability, explicitly pack that note:

   ```powershell
   python agent_workspace/memory_pack.py --root . --task <task-id> --input .agent/knowledge_base/evidence/YYYY-MM-DD-<topic>.md --summary "<bounded fact>" --scenario "<bounded context>"
   ```

   The packer copies the source to `.agent/memory/refs/<task-id>.md`, hashes it,
   and validates the resulting `.agent/memory/evidence-memory.json` before it
   returns.
3. Do not pass `--store-long-term` unless the user explicitly requests a
   long-term-memory write.
4. Write the compact summary with
   [[../templates/evidence-memory-summary]], citing the source evidence note,
   `.agent/memory/refs/<task-id>.md`, the evidence-memory document, and the L1
   atom or canonical artifact when present.
5. Keep every current-state claim under `Verified Now`; record historical or
   inferred context separately, following [[query-memory]].
6. Run the smallest relevant evidence-packer test or validator and the
   knowledge-base health audit. Update `log.md` after the evidence is verified.

## Citation Rules

- Cite paths and the source SHA-256; do not paste the raw evidence body again.
- One claim may cite multiple evidence refs. A claim without a citation is an
  interpretation, not durable evidence.
- A knowledge-base evidence note is an orientation artifact. The canonical
  evidence-memory record remains the traceable source when a memory pack exists.
- Redact secrets before either note is written. Never cite credentials, cookies,
  or unbounded environment output.

## Related Notes

- [[evidence-capture]]
- [[query-memory]]
- [[maintenance]]
- [[../templates/evidence-memory-summary]]
