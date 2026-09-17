"""Generative Engineering Specification Skill.

Converts creative intents into multi-modal engineering specification prompts
for 3D (Blender/Three.js), UI (React 19/Tailwind), and 2D (Sprites/SVG).
Adheres to the 4-part specification architecture:
1. Context & Subject
2. Hard Constraints & Design Tokens
3. Behavior, State Machine & Timeline
4. Acceptance Criteria & Critic Loop
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


class GenerativeSpecArgs(BaseModel):
    """Arguments for generating engineering specifications."""

    domain: str = Field(
        ...,
        description="Target domain. Must be one of: '3d', 'ui', '2d'.",
    )
    intent: str = Field(
        ...,
        description="Core intent or concept (e.g. 'Cyberpunk control panel', 'Dragon model', 'Mech sprite').",
    )
    target_engine: str = Field(
        "default",
        description="Target tech stack: 'blender', 'threejs', 'react', 'godot', 'spritesheet', or 'svg'.",
    )
    palette: list[str] = Field(
        default_factory=list,
        description="Optional list of Hex color codes to enforce (e.g. ['#0d1117', '#161b22', '#238636']).",
    )
    constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Optional additional key-value constraints.",
    )


def generative_spec_generator(args: GenerativeSpecArgs) -> str:
    """
    Generate a production-grade engineering specification prompt.
    Supported domains: '3d', 'ui', '2d'.
    """
    domain = args.domain.lower().strip()
    intent = args.intent.strip()
    engine = args.target_engine.lower().strip()

    if not intent:
        return "Error: Intent cannot be empty."

    if domain not in ("3d", "ui", "2d"):
        return f"Error: Unsupported domain '{domain}'. Must be '3d', 'ui', or '2d'."

    palette_str = ", ".join(args.palette) if args.palette else "Strict domain palette; zero AI saturated purple/neon"
    extra_constraints = "\n".join(f"- {k}: {v}" for k, v in args.constraints.items()) if args.constraints else "- No additional constraints specified."

    if domain == "3d":
        target = "Blender Headless Python (bpy)" if engine in ("blender", "bpy") else "Three.js / WebGL single self-contained HTML"
        spec = f"""# Engineering Specification: {intent} (3D Domain)

## 1. Context & Subject
- Objective: Create a photorealistic, coherent 3D scene/asset for '{intent}'.
- Target Engine: {target}
- Visual Tone: Anatomically/physically grounded; cinematic depth, realistic scale, and lighting.
- Color Palette: {palette_str}

## 2. Geometry & Asset Constraints
- True Geometry Only: Must be actual editable 3D geometry. Strictly forbidden: 2D billboards, parallax depth illusions, pre-rendered video.
- Modeling Pipeline: Anatomical/Structural Blockout -> Secondary Parts -> Tertiary Surface Details.
- Topology Hygiene: No coplanar intersections, no non-manifold edges, no inverted normals.
- Additional Constraints:
{extra_constraints}

## 3. Behavior, Motion & Directed Timeline
- Single Elapsed Clock: All movements driven by a single elapsed time clock; zero unseeded Math.random() loops.
- Directed Beats (Timeline):
  - [0.0s - 4.0s] Establishing View: Slow push-in, low-angle perspective, introducing focal point.
  - [4.0s - 10.0s] Dynamic Evolution: Key interaction/rotation or secondary motion unfolds.
  - [10.0s - 15.0s] Climax & Seamless Loop: Settles smoothly into beginning frame with Bézier easing.

## 4. Acceptance Criteria & Critic Loop
- Multi-Camera Setup: Configure at least 4 validation cameras (Front Ortho, Side Ortho, Top Ortho, 45° Hero Perspective).
- Critic-and-Correction Protocol: Render validation frames, inspect silhouettes, detect shading discrepancies, perform at least 2 correction passes.
- Fail Conditions:
  - Linear camera motion without acceleration/easing is an automatic FAIL.
  - Any remaining uncompleted code or dummy placeholder geometry is an automatic FAIL.
  - Performance dropping below 60 FPS is an automatic FAIL.
"""

    elif domain == "ui":
        target = "React 19 + Radix UI + Tailwind CSS" if engine in ("default", "react") else engine
        spec = f"""# Engineering Specification: {intent} (UI Domain)

## 1. Context & Role
- Objective: Build an enterprise-grade presentation component for '{intent}'.
- Target Architecture: {target}
- Visual Baseline: Dark Glassmorphism / Minimalist enterprise control plane.
- Color Palette (Strict Tokens): {palette_str}

## 2. Layout & Asset Constraints
- 8px Baseline Grid: All padding, margin, and gaps must follow standard 8px scale (8, 16, 24, 32px).
- Zero External Asset Breakage: Pure Lucide icons (named imports); no external CDN image URLs.
- Responsive Viewports: Adaptive for Desktop (1440px) and Mobile (375px); strictly `overflow-x: hidden`.
- Additional Constraints:
{extra_constraints}

## 3. State Machine & Micro-Interactions
- Required 5-State Handling:
  1. `loading`: Pulsing skeleton placeholder (no plain text/spinner-only cop-outs).
  2. `empty`: Dedicated friendly empty state with action call-to-action.
  3. `error`: Categorized error display with retry trigger.
  4. `active`: Real-time data streaming indicator with subtle value highlight.
  5. `action`: Keyboard navigation (Arrow keys, Enter, Escape) and visible focus ring.

## 4. Acceptance Criteria & Critic Loop
- Console Purity: 0 TypeScript errors, 0 React missing key warnings, 0 console errors.
- Visual Verification: Capture Playwright screenshots at 375px and 1440px.
- Fail Conditions:
  - Any untruncated text causing card overflow is an automatic FAIL.
  - Using TypeScript `any` or placeholder functions is an automatic FAIL.
"""

    else:  # 2d
        target = "2D Sprite Sheet (PNG + Metadata)" if engine in ("default", "sprite", "spritesheet") else "Vector SVG / Canvas"
        spec = f"""# Engineering Specification: {intent} (2D Domain)

## 1. Context & Perspective
- Objective: Produce clean, production-ready 2D game/visual assets for '{intent}'.
- Target Delivery: {target}
- Perspective: 2.5D Isometric (2:1) or Top-Down orthographic.
- Color Palette: {palette_str} (Restricted color depth, zero gradient pollution).

## 2. Hard Asset & Dimension Constraints
- Grid Discipline: Strict cell size (e.g. 32x32 or 64x64); power-of-two texture dimensions.
- Chroma-Key Alpha: Pure Magenta `#FF00FF` background for zero-fringe edge alpha slicing.
- Hard-edge Alignment: No stray sub-pixel anti-aliasing artifacts on sprite perimeters.
- Additional Constraints:
{extra_constraints}

## 3. Motion & Frame Sequencing
- Frame Timeline:
  - Row 1: Idle Loop (4-6 frames, natural breathing/bobbing).
  - Row 2: Walk/Move Loop (6-8 frames, distinct contact and passing phases).
  - Row 3: Action/Impact (Anticipation -> Release -> Recovery).
- Ground Anchor: Base shadow must stay locked to the horizontal baseline throughout cycles.

## 4. Acceptance Criteria & Critic Loop
- Pixel Consistency: No floating body parts or jittering pivot points between animation frames.
- Automated Edge Scan: Pixel count audit verifies 0 color bleed outside specified palette.
- Fail Conditions:
  - Missing ground contact alignment is an automatic FAIL.
  - Palette mismatch or muddy transparency is an automatic FAIL.
"""

    return spec
