---
id: generative_spec_generator
name: generative_spec_generator
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

# generative_spec_generator

> **PAP Skill Contract**: This document defines the exact execution boundaries, inputs, and outputs for this skill.

## 1. Purpose

Transforms unstructured user prompts into production-ready engineering specification prompts across 3D, UI, and 2D design spaces.
Enforces the 4-part architecture:
1. Context & Subject
2. Hard Constraints & Design Tokens
3. Behavior, State Machine & Timeline
4. Acceptance Criteria & Critic Loop

## 2. Required Inputs

- `domain` (string, **Required**): Target domain ('3d', 'ui', '2d').
- `intent` (string, **Required**): Core creative or functional intent.
- `target_engine` (string, Optional): Tech stack target.
- `palette` (array of strings, Optional): Specific Hex color codes.
- `constraints` (object, Optional): Custom constraint dictionary.

## 3. Expected Outputs

- **Success format**: Markdown specification with numbered section headers.
- **Error format**: String prefixed with `Error:`.

## 4. Execution Boundaries and Safety

- Deterministic pure computation.
- No network requests, no subprocess spawning, no filesystem changes.
- Bounded input sizes.

## 5. Runtime Mapping

- Module: `agent_workspace.skills.generative_spec_generator`
- Function: `generate_spec`
- Argument Class: `GenerativeSpecArgs`
