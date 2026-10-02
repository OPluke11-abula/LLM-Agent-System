"""Closed-Loop Refactoring Experience Distillation Engine (Phase 103).

Extracts reusable engineering patterns and defect prevention lessons from completed
refactoring tasks and adversarial debates, committing them directly to FederatedVectorMemory
with cryptographic Merkle proof updates.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from agent_workspace.core.factory.adversarial_committee import AdversarialDebateRecord
from agent_workspace.core.factory.models import RefactoringTaskNode
from agent_workspace.core.vector_memory import (
    FederatedVectorMemory,
    VectorCategory,
    VectorMemoryEntry,
)

logger = logging.getLogger("PatternDistillation")


class PatternDistillationEngine:
    """Distills refactoring successes and defect lessons into cryptographically verifiable vector memory."""

    def __init__(self, vector_memory: Optional[FederatedVectorMemory] = None) -> None:
        self.vector_memory = vector_memory or FederatedVectorMemory(node_id="node-factory-distiller")
        self.distilled_entries: List[VectorMemoryEntry] = []

    def distill_task_outcome(
        self,
        task: RefactoringTaskNode,
        debate: Optional[AdversarialDebateRecord] = None,
        execution_success: bool = True,
        execution_details: Optional[Dict[str, Any]] = None,
    ) -> List[VectorMemoryEntry]:
        """Distills a completed task into PATTERN and LESSON vector memory entries."""
        new_entries: List[VectorMemoryEntry] = []
        details = execution_details or {}
        timestamp = time.time()

        # 1. Distill PATTERN (Best Practice / Proven Blueprint)
        if execution_success:
            pattern_content = (
                f"Refactoring Blueprint for {task.task_type.value} on {task.title}.\n"
                f"Mutable Scopes: {', '.join(task.mutable_scope)}.\n"
                f"Execution Strategy: Decoupled into wave-isolated units. "
                f"Estimated Effort: {task.estimated_effort}/10."
            )
            if debate and debate.self_healing_contract:
                pattern_content += (
                    f"\nMandatory Assertions Verified: {len(debate.self_healing_contract.mandatory_test_assertions)}. "
                    f"Consensus Score: {debate.consensus_score}."
                )

            pattern_entry = self.vector_memory.store(
                task_id=task.node_id,
                category=VectorCategory.PATTERN,
                content=pattern_content,
                metadata={
                    "task_type": task.task_type.value,
                    "target_files": task.target_files,
                    "mutable_scope": task.mutable_scope,
                    "consensus_score": debate.consensus_score if debate else 100.0,
                    "distilled_at": timestamp,
                },
                author_node_id=self.vector_memory.node_id,
                timestamp=timestamp,
            )
            new_entries.append(pattern_entry)
            self.distilled_entries.append(pattern_entry)

        # 2. Distill LESSON (Vulnerabilities caught, mitigations, failure recovery)
        if debate and debate.vulnerabilities_detected:
            mitigated_vulns = [v for v in debate.vulnerabilities_detected if v.resolved]
            if mitigated_vulns:
                lesson_content = (
                    f"Defect Prevention Lesson for {task.task_type.value} ({task.title}):\n"
                    + "\n".join(
                        f"- [{v.severity.value}] {v.category}: {v.description} -> Mitigated via: {v.mitigation_plan}"
                        for v in mitigated_vulns
                    )
                )
                lesson_entry = self.vector_memory.store(
                    task_id=task.node_id,
                    category=VectorCategory.LESSON,
                    content=lesson_content,
                    metadata={
                        "task_type": task.task_type.value,
                        "vulnerability_count": len(mitigated_vulns),
                        "categories": [v.category for v in mitigated_vulns],
                        "distilled_at": timestamp,
                    },
                    author_node_id=self.vector_memory.node_id,
                    timestamp=timestamp,
                )
                new_entries.append(lesson_entry)
                self.distilled_entries.append(lesson_entry)

        merkle_root = self.vector_memory.compute_merkle_root()
        logger.info(
            "[PatternDistillation] Distilled %d entries for task %s (Merkle Root: %s...)",
            len(new_entries),
            task.node_id,
            merkle_root[:8],
        )
        return new_entries

    def get_merkle_root(self) -> str:
        """Returns the current Merkle tree root hash of the vector memory."""
        return self.vector_memory.compute_merkle_root()

    def get_distilled_patterns(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieves summary dicts of distilled experience patterns."""
        results = []
        for entry in reversed(self.distilled_entries[-top_k:]):
            results.append({
                "entry_id": entry.entry_id,
                "task_id": entry.task_id,
                "category": entry.category.value,
                "content": entry.content,
                "content_hash": entry.content_hash,
                "timestamp": entry.timestamp,
                "metadata": entry.metadata,
            })
        return results
