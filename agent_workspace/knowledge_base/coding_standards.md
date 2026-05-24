---
id: coding_standards
title: "LAS Coding Standards"
description: "Coding standards, quality checklists, and testing policies."
creator: "LAS Lead Developer"
version: "1.1.0"
tags:
  - standards
  - guidelines
  - testing
---

# LAS Coding Standards

This document establishes the authoritative coding conventions and validation checklists for developers and AI agents extending LAS.

## 1. Type Hints and Strict Validation
- All Python functions must declare full type signatures and Pydantic validators where appropriate.
- Prefer standard type hints over legacy typing annotations.

## 2. Test-Driven Development (TDD)
- Extend test coverage alongside every newly added feature or component.
- Ensure all tests reside within `agent_workspace/tests/` and are executable using standard `pytest`.
