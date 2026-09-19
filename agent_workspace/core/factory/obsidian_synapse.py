"""Obsidian Living Architecture Backlink Synchronizer (Phase 103).

Generates semantic bi-directional Wikilink Markdown documents for distilled refactoring
patterns, integrating them directly into the 4-tier Obsidian knowledge topology.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from agent_workspace.core.vector_memory import VectorMemoryEntry

logger = logging.getLogger("ObsidianSynapse")


class ObsidianSynapseSynchronizer:
    """Synchronizes newly distilled software factory patterns into Obsidian Vault topology."""

    def __init__(self, obsidian_dir: Optional[Path] = None) -> None:
        self.obsidian_dir = Path(obsidian_dir) if obsidian_dir else Path("docs/obsidian")

    def generate_pattern_note(
        self,
        entry: VectorMemoryEntry,
        output_dir: Optional[Path] = None,
    ) -> str:
        """Generates a structured Markdown leaf note with canonical Wikilinks for a distilled pattern."""
        target_dir = output_dir or (self.obsidian_dir / "modules" / "factory")
        target_dir.mkdir(parents=True, exist_ok=True)

        note_name = f"pattern-{entry.task_id}.md"
        note_path = target_dir / note_name

        content = f"""---
tags:
  - factory/pattern
  - memory/vector-experience
  - protocol/v3.8.0
category: {entry.category.value}
task_id: {entry.task_id}
entry_id: {entry.entry_id}
content_hash: {entry.content_hash}
author_node: {entry.author_node_id}
---

# Distilled Pattern: `{entry.task_id}`

> **Parent Index**: [[00 LLM-Agent-System Index]]
> **ADR Reference**: [[60 Architectural Decision Records (ADR) Graph#ADR-006|ADR-006: Agent Strategy Integration]]
> **Subsystem**: [[layers/L4-Cognitive-and-Memory-OS]]

---

## 1. Distilled Experience Summary
{entry.content}

---

## 2. Cryptographic Receipts & Verification
- **Entry ID**: `{entry.entry_id}`
- **Task Link**: `{entry.task_id}`
- **Content SHA-256**: `{entry.content_hash}`
- **Timestamp**: `{entry.timestamp}`

---

## 3. Semantic Cross-Links
- [[modules/core/core-vector-memory|Federated Vector Memory Subsystem]]
- [[30 Concurrency Lifecycle & Swarm State Machine|Swarm Concurrency Lifecycle]]
- [[05 Task Status & Multi-Agent Execution DAG|Multi-Agent Task Execution DAG]]
"""
        note_path.write_text(content, encoding="utf-8")
        logger.info("[ObsidianSynapse] Written pattern note: %s", note_path)
        return str(note_path)
