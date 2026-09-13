---
tags:
  - architecture/leaf
  - skills/generative
  - tools/specification
  - layer/l2
type: module_leaf
layer: L2-Protocol-and-Contract-Gateways
module: skills
file_path: agent_workspace/skills/generative_spec_generator.py
sync_status: verified
---

# Module: SpecDrivenGenerativeEngine (Multi-Modal Engineering Specification Pipeline)

## 1. Three-Line Architectural Annotation
- **Responsibility**: Translates unstructured creative and feature intents into deterministic 4-part engineering specification prompts across 3D, UI, and 2D domains.
- **Invariant**: Generated specifications strictly forbid unconstrained descriptors (e.g. "pretty", "modern") in favor of numerical Design Tokens, strict Hex palettes, exact state machines, and mandatory multi-angle Critic Loops.
- **Data Flow**: Invoked via `GenerativeSpecArgs` by ProductOwner, Architect, or FrontendDev roles, processed by `generate_spec`, and statically validated through `scripts/verify_spec_asset.py`.

---

## 2. Core Four-Part Specification Architecture

$$\text{1. Context \& Subject} \longrightarrow \text{2. Hard Constraints \& Tokens} \longrightarrow \text{3. Behavior, State \& Timeline} \longrightarrow \text{4. Acceptance \& Critic Loop}$$

| Domain Dimension | 3D (Blender / Three.js / WebGL) | UI (React 19 / Tailwind / Radix) | 2D (Sprites / Vectors / Tiles) |
| :--- | :--- | :--- | :--- |
| **1. Context & Subject** | Physical realism, cinematic lighting, focal depth, camera lens. | Persona, business workflows, dark glassmorphism desktop theme. | Perspective (2.5D Isometric 2:1 / Top-Down), world setting. |
| **2. Hard Constraints & Tokens** | True 3D geometry only (no 2D billboard cop-outs), locked Hex palette. | 8px baseline grid, named Lucide icons, strict Hex tokens, no `any`. | Fixed cell dimensions (32x32 / 64x64), 16-color limit, `#FF00FF` Chroma-key. |
| **3. Behavior & Timeline** | Directed timeline beats (0-4s, 4-10s, 10-15s), single elapsed clock. | Mandatory 5-state machine (Loading, Empty, Error, Active, Action). | Frame sequences (Idle 4f, Walk 6f, Action), ground anchor alignment. |
| **4. Acceptance & Critic Loop** | 4-camera validation renders, inspection passes, fail on linear orbit. | Multi-viewport screenshots (375px/1440px), 0 console warnings. | 0 color bleed outside palette, baseline shadow stability audit. |

---

## 3. Concrete Source Bindings & Implementation Manifest

| Component | File Path | Exact Function / Entrypoint | Responsibility |
| :--- | :--- | :--- | :--- |
| **Local Runtime Skill** | `agent_workspace/skills/generative_spec_generator.py` | `generate_spec(args: GenerativeSpecArgs)` | Pure Python + Pydantic reflection skill |
| **PAP v0.2 Contract** | `.agent/skills/generative_spec_generator.md` | Skill ID: `generative_spec_generator` | Execution boundary & schema definition |
| **Skill Registry** | `.agent/skills.md` | Table entry: `generative_spec_generator` | Maps runtime module to PAP contract |
| **Local Workspace Skill** | `skills/generative-spec-pipeline/SKILL.md` | Markdown Skill definition | Antigravity discovery & prompt templates |
| **Automated Auditor** | `scripts/verify_spec_asset.py` | `audit_spec_text(content, domain)` | Static compliance and invariant validator |

---

## 4. Operational Invariants & Anti-Corruption Guardrails

1. **Zero Placeholder Invariant**:
   - `scripts/verify_spec_asset.py` enforces zero tolerance for `// TODO`, `FIXME`, `TBD`, or placeholder tokens.
2. **Defensive Isolation (`SandboxGuard`)**:
   - The generator is a deterministic, pure-computation utility. It makes no network requests, spawns no subprocesses, and touches no unauthorized filesystem paths.
3. **Hard Token Enforcement**:
   - Prohibits unconstrained AI color generation (e.g. saturated purple/cyan glow) by requiring explicit Hex arrays (e.g. `['#0d1117', '#161b22', '#238636']`).
4. **Typed Failures Only**:
   - Missing intents or unsupported domains strictly return descriptive `Error: ...` strings without throwing unhandled exceptions.

---

## 5. Verification & Test Evidence

- **Bytecode Compilation**:
  - `python -m py_compile agent_workspace/skills/generative_spec_generator.py scripts/verify_spec_asset.py`
  - **Result**: Exit code `0` (PASS).
- **Multi-Domain Unit Verification**:
  - Validated across 3D (`Gothic Cathedral`), UI (`Agent Monitor Dashboard`), and 2D (`Pixel Mech`).
  - **Result**: All 3 domains passed with 0 invariant violations.
- **Static Auditor CLI Self-Test**:
  - `python scripts/verify_spec_asset.py --domain 3d --content "..."` $\rightarrow$ Exit code `0` (`[PASS]`).
  - Negative placeholder test (`// TODO`) $\rightarrow$ Exit code `1` (`[FAIL]`, correctly identified 6 structural/placeholder violations).

---

## 6. Topological Linkage

- **Upstream Layer**: [[L2-Protocol-and-Contract-Gateways]]
- **Parent Catalog**: [[skills-inventory-and-tools]]
- **Roles Matrix**: [[70 Multi-Agent Protocol v3.8.0 & 10 Grounded Roles Matrix]]
- **Collaborating Modules**:
  - [[core-router]]
  - [[core-sandbox]]
