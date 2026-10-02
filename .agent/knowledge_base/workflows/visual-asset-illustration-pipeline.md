# Visual Asset and Illustration Pipeline

## Purpose

Choose, produce, store, and verify LAS Viewer visual assets without turning the
`Cognitive Operations Atlas` into decoration. An asset is justified only when it
communicates state, structure, evidence, or an interaction model more clearly than
the existing DOM and type system.

## Asset Choice Gate

Use the least complex medium that preserves the meaning.

| Medium | Use when | Do not use when | Required fallback |
| --- | --- | --- | --- |
| Generated bitmap | A self-authored atmospheric substrate, empty-state scene, texture, or concept study needs visual depth that CSS or vectors cannot express economically. | The image would contain UI text, controls, live state, evidence, logos, protected trade dress, or information that must remain crisp at arbitrary zoom. | A neutral color/gradient field plus the same text and actions in the DOM. |
| Diagram | A process, dependency, trust boundary, proof path, or layer relationship is the subject. Prefer Mermaid in documentation and semantic SVG/DOM in the product. | A list, table, or short sequence communicates the same relationship more directly. | Ordered text or a table preserving nodes, edges, direction, and status. |
| Screenshot | Current LAS behavior or a visual-QA result must be evidenced, annotated, or compared. | The image is decorative, stale, conceals an unresolved state, or is being used instead of implementing the UI. | Route, viewport, build/ref, capture time, and a written finding. |
| SVG composition | A bounded atlas layer, route, proof trail, icon, or responsive vector illustration needs selectable or accessible structure. | The node count or update rate makes DOM/SVG rendering impractical. | Text summary and tabular state; static PNG only as a secondary export. |
| Canvas composition | Dense, high-frequency topology or terrain rendering exceeds practical SVG/DOM limits and performance has been measured. | Keyboard navigation, selectable text, or semantic inspection would exist only inside the bitmap surface. | Synchronized DOM inspector/list, accessible summary, and non-canvas empty/error state. |
| Figma mockup | Composition, hierarchy, asset framing, or a high-risk interaction needs review before implementation. | It would become a runtime dependency, source of truth for live data, or substitute for repository acceptance criteria. | Exported local reference plus written measurements, tokens, states, and acceptance notes. |

When two media qualify, prefer DOM/CSS, then SVG, then canvas, then bitmap. A
Figma or generated-image study informs implementation; it is not production code.

## Production Record

Before an asset enters the viewer, record:

- purpose and owning surface;
- asset type and why a simpler medium was insufficient;
- source path, generation prompt/tool or source URL, author, license, and date;
- approved variant, dimensions, focal point, and responsive behavior;
- accessibility text, loading behavior, and empty/error fallback;
- optimization result and screenshot evidence paths.

Keep this record beside the asset in a `README.md` or in the design packet that
links to it. Never store credentials, customer data, private prompts, or sensitive
screens in an asset or its metadata.

## Local Storage and Naming

- Production static assets live under `viewer/public/assets/<surface>/` when they
  must retain stable public filenames, or `viewer/src/assets/<surface>/` when the
  build should fingerprint and bundle them. Prefer imported `src/assets` files.
- Design sources and mockup exports live under
  `.agent/knowledge_base/assets/phase-<nn>/<surface>/`; screenshot evidence stays
  under the verifier's existing `viewer/output/` structure.
- Do not hotlink runtime imagery. External references are research evidence and
  must be converted into an authorized local derivative or replaced.
- Name files `<surface>-<role>-<variant>-<width>.<ext>` in lowercase kebab case;
  omit the width for vectors. Keep editable sources distinct from optimized
  runtime exports.
- Remove abandoned variants rather than leaving ambiguous `final-v2` files. The
  production record identifies the approved file.

## Accessibility Contract

- Informative images require concise alt text describing their operational
  meaning, not their appearance. Adjacent DOM content must carry exact values.
- Decorative assets use `alt=""` or `aria-hidden="true"` and cannot encode state.
- SVG figures use a visible caption or an accessible name and description. Focused
  nodes and routes expose the same label, state, and action through the DOM.
- Canvas surfaces provide a synchronized keyboard-operable list or inspector and
  a live text summary for material state changes.
- Never rely on color, texture, animation, crop, or spatial position alone. Labels,
  shapes, and status text must preserve blocked, pending, active, and verified
  distinctions.
- Animated assets obey `prefers-reduced-motion`; the static equivalent must show
  the final state and current selection without losing information.

## Responsive Framing and Cropping

- Record a normalized focal point for every raster image and set explicit
  `object-position` rather than accepting an accidental center crop.
- Define desktop, tablet, and mobile aspect behavior. Supply deliberate variants
  when one crop cannot preserve the subject; do not stretch an image.
- Never crop labels, evidence markers, route endpoints, selected objects, or
  safety-relevant state. Semantic content belongs in responsive DOM/SVG when a
  crop could hide it.
- Mobile may simplify density, routes, or texture, but must retain the focal
  object, current state, next action, and accessible equivalent.
- Reserve intrinsic dimensions or `aspect-ratio` to prevent layout shift, and
  verify long labels and localized text independently of the image.

## Optimization Gate

- Prefer SVG for authored vectors, AVIF/WebP for photographic or generated raster
  assets, and PNG only when transparency or lossless pixel evidence requires it.
- Export raster assets no larger than their maximum rendered density needs; use
  responsive sources when a single file would overserve mobile.
- Strip unnecessary metadata and embedded profiles, preserve only required
  provenance in the production record, and optimize SVG paths without removing
  accessible titles, descriptions, or stable test hooks.
- Lazy-load below-the-fold illustration assets. Do not lazy-load the first focal
  object when doing so would delay comprehension; preload only measured critical
  assets.
- Reject an asset that causes visible blur, banding, unreadable overlays, layout
  shift, or a material bundle/network regression. Record exceptions with measured
  evidence and an owner.

## Screenshot Verification Gate

1. Build the current viewer and capture from that build, not a stale dev tab.
2. Capture the changed route at its canonical desktop and mobile viewports; add a
   tablet or interaction state when cropping, overflow, hover, focus, motion, or a
   dense canvas can change the result.
3. Include loading, empty, error, selected, and reduced-motion states when the
   asset participates in them.
4. Inspect focal-object framing, crop safety, text contrast, keyboard focus,
   accessible equivalent, layout shift, asset sharpness, and state parity.
5. Store evidence under `viewer/output/` using the existing verifier convention and
   record route, viewport, build/ref, capture time, and finding disposition.
6. Run the relevant viewer build and screenshot verifier. Passing scripts prove
   execution only; a design reviewer must still assess coherence and craft.

An asset is not accepted when desktop passes but mobile hides its subject, when a
canvas lacks a semantic equivalent, when generated content resembles protected
trade dress, or when the evidence cannot be tied to the current build.

## Handoff Checklist

- [ ] Medium choice and simpler alternatives are recorded.
- [ ] Source, author/tool, prompt or URL, license, date, and approved file are known.
- [ ] Runtime assets are local and use deterministic names.
- [ ] Accessible label, semantic equivalent, and reduced-motion state exist.
- [ ] Desktop/mobile framing and focal points are explicit.
- [ ] Format, dimensions, loading behavior, and metadata are optimized.
- [ ] Fresh route screenshots demonstrate the current build and required states.
- [ ] Design review found no unresolved asset-quality or protected-trade-dress risk.

## Related Notes

- [[visual-reference-moodboard]]
- [[../exports/phase-71-las-viewer-art-direction-packet-2026-07-07]]
- [[../exports/phase-71-screen-composition-studies-2026-07-07]]
