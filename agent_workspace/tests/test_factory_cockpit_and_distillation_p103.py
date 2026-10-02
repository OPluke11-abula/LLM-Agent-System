"""Unit and integration tests for Closed-Loop Experience Distillation & Factory Cockpit (Phase 103).

Validates pattern and lesson distillation to FederatedVectorMemory, Obsidian synapse notes,
FastAPI /v1/factory/* endpoints, and golden factory benchmark receipts.
"""

import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.factory import (
    AdversarialDebateRecord,
    ObsidianSynapseSynchronizer,
    PatternDistillationEngine,
    RefactoringTaskNode,
    RefactoringTaskType,
    SelfHealingContract,
    VulnerabilitySeverity,
    VulnerabilityVector,
)
from agent_workspace.core.vector_memory import FederatedVectorMemory, VectorCategory
from scripts.run_factory_benchmark import run_golden_factory_benchmark


def test_pattern_distillation_engine():
    """Validates that completed tasks are distilled into PATTERN and LESSON vector entries."""
    vmem = FederatedVectorMemory(node_id="test-distiller")
    distiller = PatternDistillationEngine(vector_memory=vmem)

    task = RefactoringTaskNode(
        node_id="task-distill-test",
        title="Async I/O Optimization",
        task_type=RefactoringTaskType.ASYNC_MIGRATION,
        target_files=["agent_workspace/core/engine.py"],
        mutable_scope=["agent_workspace/core/engine.py"],
    )

    debate = AdversarialDebateRecord(
        task_id=task.node_id,
        task_title=task.title,
        consensus_score=95.0,
        quorum_reached=True,
        vulnerabilities_detected=[
            VulnerabilityVector(
                category="CONCURRENCY_RACE",
                description="Un-awaited coroutine",
                severity=VulnerabilitySeverity.HIGH,
                resolved=True,
                mitigation_plan="Applied asyncio.to_thread and timeout guards",
            )
        ],
        self_healing_contract=SelfHealingContract(
            task_id=task.node_id,
            mandatory_test_assertions=["assert exit code == 0"],
            rollback_triggers=["Test ladder failure"],
        ),
    )

    entries = distiller.distill_task_outcome(task, debate, execution_success=True)

    assert len(entries) == 2  # 1 PATTERN, 1 LESSON
    categories = {e.category for e in entries}
    assert VectorCategory.PATTERN in categories
    assert VectorCategory.LESSON in categories

    merkle_root = distiller.get_merkle_root()
    assert len(merkle_root) == 64  # SHA-256 hex string

    patterns = distiller.get_distilled_patterns()
    assert len(patterns) >= 2


def test_obsidian_synapse_note_generation():
    """Validates Markdown generation with Wikilinks for distilled vector memory entries."""
    vmem = FederatedVectorMemory(node_id="test-obsidian")
    distiller = PatternDistillationEngine(vector_memory=vmem)

    task = RefactoringTaskNode(
        node_id="task-obsidian-01",
        title="Decouple Core Router",
        task_type=RefactoringTaskType.DECOUPLING,
        target_files=["agent_workspace/core/router.py"],
    )

    entries = distiller.distill_task_outcome(task, execution_success=True)
    assert len(entries) >= 1
    pattern_entry = entries[0]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_obsidian = Path(tmpdir)
        synapse = ObsidianSynapseSynchronizer(obsidian_dir=tmp_obsidian)
        note_path_str = synapse.generate_pattern_note(pattern_entry)

        note_path = Path(note_path_str)
        assert note_path.is_file()
        content = note_path.read_text(encoding="utf-8")

        assert "[[00 LLM-Agent-System Index]]" in content
        assert "[[60 Architectural Decision Records (ADR) Graph#ADR-006" in content
        assert pattern_entry.entry_id in content
        assert pattern_entry.content_hash in content


def test_fastapi_factory_routes():
    """Validates FastAPI /v1/factory endpoints with TestClient."""
    client = TestClient(app)

    # 1. GET /v1/factory/overview
    res_overview = client.get("/v1/factory/overview")
    assert res_overview.status_code == 200
    data = res_overview.json()
    assert data["status"] == "ONLINE"
    assert "total_modernized_loc" in data
    assert "quorum_success_rate" in data
    assert "merkle_root" in data

    # 2. GET /v1/factory/patterns
    res_patterns = client.get("/v1/factory/patterns")
    assert res_patterns.status_code == 200
    patterns = res_patterns.json()
    assert isinstance(patterns, list)

    # 3. POST /v1/factory/run-pipeline
    payload = {
        "target_directory": "agent_workspace/core/factory",
        "goal": "FastAPI Route Modernization Test",
        "max_tasks": 3,
    }
    res_run = client.post("/v1/factory/run-pipeline", json=payload)
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["status"] == "COMPLETED"
    assert run_data["total_tasks"] >= 1
    assert run_data["total_waves"] >= 1
    assert "merkle_root" in run_data
    assert len(run_data["debates"]) >= 1


def test_golden_factory_benchmark_execution():
    """Validates end-to-end golden factory benchmark script execution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        receipt_file = tmp_path / "factory_golden_receipt.json"

        receipt = run_golden_factory_benchmark(
            target_dir=Path("agent_workspace/core/factory"),
            output_file=receipt_file,
        )

        assert receipt["status"] == "PASS"
        assert receipt["verifications"]["scope_isolation"] == "PASS"
        assert receipt["verifications"]["quorum_enforcement"] == "PASS"
        assert receipt["verifications"]["merkle_chain_integrity"] == "PASS"
        assert receipt["metrics"]["scope_isolation_violations"] == 0
        assert receipt["metrics"]["quorum_approved"] > 0
        assert receipt["metrics"]["distilled_patterns_count"] > 0
        assert receipt_file.is_file()
