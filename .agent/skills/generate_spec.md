---
id: generate_spec
name: generate_spec
description: 'Generate production-grade multi-modal engineering specifications for 3D, UI, and 2D development with strict constraints, state/timeline definitions, and critic-and-correction loops.'
version: 1.0.0
inputs:
  domain:
    type: string
    required: true
    description: "Target domain. Must be one of: '3d', 'ui', '2d'."
  intent:
    type: string
    required: true
    description: "Core intent or concept (e.g. 'Cyberpunk control panel', 'Dragon model', 'Mech sprite')."
  target_engine:
    type: string
    required: false
    description: "Target tech stack: 'blender', 'threejs', 'react', 'godot', 'spritesheet', or 'svg'."
  palette:
    type: array
    required: false
    description: "Optional list of Hex color codes to enforce."
  constraints:
    type: object
    required: false
    description: "Optional additional key-value constraints."
outputs:
  success:
    type: string
    description: Markdown engineering specification prompt.
  error:
    type: string
    description: String prefixed with Error:.
safety_notes:
- Deterministic specification generator; no file mutation or network calls.
- Validates domain against allowlist ('3d', 'ui', '2d').
- Safe against prompt injection by enforcing structured templating.
author: LAS Tool Manifest
---

# generate_spec

Generate strict, production-grade engineering specification prompts for generative models and workflows across 3D, UI, and 2D disciplines.
