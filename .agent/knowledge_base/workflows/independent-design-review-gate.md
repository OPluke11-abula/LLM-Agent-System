# Independent Design Review Gate

## Purpose

Prevent LAS Viewer implementation phases from closing on build success alone.
This gate evaluates the current interface against the approved `Cognitive
Operations Atlas` direction, converts observable design defects into executable
tasks, and preserves the evidence needed to reproduce every judgment.

## Independence Rule

The reviewer must not be the person or agent that made the implementation under
review. The reviewer may inspect source to understand behavior but must score the
rendered result rather than defend implementation choices.

If an independent reviewer is unavailable, record the review as `provisional`.
A provisional review can produce findings and unblock investigation, but it
cannot close a major design phase or mark the gate `pass`.

## Required Evidence

Review the smallest current evidence set that covers the changed experience:

- the active task and acceptance criteria from `.agent/agent_tasks.md`;
- `viewer/DESIGN.md` and the approved art-direction/composition packet;
- fresh screenshots from the current build at canonical desktop and mobile
  viewports;
- tablet, interaction, loading, empty, error, blocked, focus, and reduced-motion
  evidence when the change can affect those states;
- the relevant route in a working viewer for keyboard path, motion, overflow,
  text fit, and interaction checks;
- prior open design findings for the same surface.

Record the build/ref, route, viewport, capture time, evidence path, and reviewer.
Stale screenshots, mockups, or code inspection alone cannot close the gate.

## Scoring Scale

Score each dimension with an integer from 0 to 4.

| Score | Meaning |
| ---: | --- |
| 0 | Missing, broken, or actively harmful. |
| 1 | Major failure; the intended quality is mostly absent. |
| 2 | Functional but visibly unresolved or inconsistent. |
| 3 | Strong and implementation-ready with only minor defects. |
| 4 | Deliberate, polished, coherent, and evidenced across required states. |

Do not average away a missing state. Score the weakest material state or viewport
and capture a finding for the variance.

## Weighted Rubric

| Dimension | Weight | Review questions |
| --- | ---: | --- |
| Coherence | 15 | Does the surface belong to the same atlas system, with consistent material, component, and state grammar? |
| Craft | 15 | Are details intentional, assets sharp, states complete, and controls free of placeholder or code-first roughness? |
| Hierarchy | 15 | Is one focal object clear, is the first viewport purposeful, and does the scan path lead to state and next action? |
| Typography | 10 | Are type roles, line lengths, labels, numerals, wrapping, and density deliberate across viewports? |
| Color | 10 | Does color communicate semantic state with adequate contrast and restrained, art-directed use? |
| Spacing | 10 | Do rhythm, alignment, grouping, density, and breathing room reinforce information relationships? |
| Motion | 5 | Does motion explain change or focus, stay responsive, and preserve meaning with reduced motion? |
| Accessibility | 15 | Are keyboard path, focus, touch targets, reading order, text fit, contrast, and non-color semantics usable? |
| Vibe-coded risk | 5 | Is the result specific to LAS rather than a generic dark dashboard, card collage, glow treatment, or copied trade dress? A higher score means lower risk. |

Compute the weighted result as:

`sum(score / 4 * weight)`

Round only the final result to a whole number. The report must preserve all raw
dimension scores and evidence notes.

## Gate Decision

The reviewer assigns exactly one result:

- `pass`: weighted score is at least 85, every dimension scores at least 3,
  required evidence is current, and no open P0/P1 finding remains.
- `conditional`: weighted score is 70-84, every dimension scores at least 2,
  and no hard-fail condition exists. Findings must be scheduled before release.
- `fail`: weighted score is below 70 or any hard-fail condition exists.
- `provisional`: the evidence was reviewed by the implementer or another
  independence requirement could not be satisfied.

Hard-fail conditions:

- current desktop or mobile evidence is missing for an affected responsive
  surface;
- a critical workflow, focal object, state, or next action is absent or unusable;
- keyboard access, visible focus, readable contrast, non-color state semantics,
  or reduced-motion equivalence materially fails;
- protected assets, distinctive trade dress, sensitive data, or unlicensed
  material appears in the result;
- a P0/P1 design finding remains open;
- the review cannot tie its evidence to the current build/ref.

## Finding-to-Task Contract

Every score below 3 and every discrete defect must become a task in
`.agent/agent_tasks.md`; the report is not the task tracker. Use stable IDs:

`DESIGN-YYYYMMDD-NN`

Each task must contain:

- checkbox status, stable ID, P0-P3 priority, surface, and short observable title;
- evidence path plus route, viewport/state, and build/ref;
- failed rubric dimension and observed behavior;
- user or operational impact;
- bounded remediation intent without prescribing unnecessary implementation;
- owner or role, acceptance criteria, and exact verification evidence needed;
- dependency or blocker when applicable.

Use this task shape:

```markdown
- [ ] `DESIGN-YYYYMMDD-NN` `[P2]` **Surface - observable defect**
  - Dimension: Hierarchy
  - Evidence: `viewer/output/<run>/<file>.png`; route, viewport/state, build/ref
  - Impact: What the user cannot understand or do reliably
  - Remediation: Bounded design outcome
  - Owner: Frontend Programmer / Visual Designer / Design Systems Programmer
  - Acceptance: Observable pass condition
  - Verify: Fresh screenshot or interaction evidence plus relevant command
  - Depends on: ID or `none`
```

Add findings under the active implementation phase or a clearly named `Open
Design Findings` subsection. Do not mark the review task complete until all
findings have stable IDs and owners. Do not close a finding because code changed;
close it only after the required fresh evidence passes independent review.

## Procedure

1. Confirm independence, scope, current build/ref, routes, states, and prior open
   findings.
2. Run the relevant viewer build and screenshot verifier, then inspect the live
   route and fresh captures.
3. Score all nine dimensions independently before calculating the total.
4. Record evidence and one concise rationale for every score.
5. Apply hard-fail conditions and assign the gate result.
6. Convert every score below 3 and every observable defect into a tracked task.
7. Write the report using [[../templates/design-review-report]].
8. Link the report and finding IDs from `.agent/agent_tasks.md`.
9. Re-review failed findings from fresh evidence; never overwrite the original
   report or silently change its score.

## Review Boundaries

- A passing build or screenshot script proves execution, not design quality.
- Personal preference is not evidence. Tie judgments to the approved direction,
  task intent, operational comprehension, accessibility, or observed behavior.
- Do not reward decorative complexity. Visual assets and motion must communicate
  state, structure, or interaction.
- Do not penalize operational density by default. Penalize unclear grouping,
  weak hierarchy, illegible type, or unnecessary repetition.
- Do not invent findings to make a review look rigorous. Record `not observed`
  when current evidence does not support a claim.

## Related Notes

- [[visual-reference-moodboard]]
- [[visual-asset-illustration-pipeline]]
- [[../templates/design-review-report]]
- [[../exports/phase-71-las-viewer-art-direction-packet-2026-07-07]]
- [[../exports/phase-71-screen-composition-studies-2026-07-07]]
