---
id: core_architecture
title: "Core System Architecture"
description: "Detailed system architectural design guidelines and boundaries."
creator: "FindAi Studio Core Team"
version: "1.0.0"
tags:
  - architecture
  - guidelines
  - pap
---

# Core System Architecture

This document outlines the core system design guidelines and service boundaries for the FindAi Studio LLM Agent System (LAS).

## 1. Principles of Separation
- Core engine and execution components reside exclusively in `agent_workspace/core/`.
- Dynamic adapters (CLI, FastAPI servers, adapters, presentation layers) reside outside core libraries.
- All persistent agent memory (episodic, semantic, handoffs) remains governed and pluggable.

## 2. Directory Structure Conventions
- `.agent/` holds declarative, portable contracts (skills, identity, tasks, prompts).
- `agent_workspace/` houses the active Python runtime execution stack.
