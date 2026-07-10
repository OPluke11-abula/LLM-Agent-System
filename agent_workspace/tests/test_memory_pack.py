import json
from pathlib import Path

from agent_workspace.long_term_memory import LongTermMemoryStore
from agent_workspace.memory_pack import pack_evidence
from agent_workspace.evidence_memory_validate import (
    EvidenceMemoryValidationError,
    validate_evidence_memory_document,
)


def test_pack_evidence_writes_ref_atom_scenario_persona_and_canvas(tmp_path):
    raw_output = tmp_path / "outputs" / "raw-test-output.txt"
    raw_output.parent.mkdir(parents=True)
    raw_output.write_text("pytest output\n5 passed\n", encoding="utf-8")

    result = pack_evidence(
        root=tmp_path,
        task_id="TASK-0001",
        input_path=raw_output,
        summary="Focused pytest passed for workflow linter.",
        scenario="Workflow linter verification completed with focused tests.",
        persona="Prefer exact command results over memory-only summaries.",
    )

    ref_path = tmp_path / result.result_ref
    atom_path = tmp_path / ".agent" / "memory" / "l1-atoms.jsonl"
    scenario_path = tmp_path / ".agent" / "memory" / "l2-scenarios" / "TASK-0001.md"
    persona_path = tmp_path / ".agent" / "memory" / "l3-persona.md"
    canvas_path = tmp_path / result.canvas_ref
    evidence_memory_path = tmp_path / result.evidence_memory_ref

    assert ref_path.read_text(encoding="utf-8").endswith("pytest output\n5 passed\n")

    atoms = [json.loads(line) for line in atom_path.read_text(encoding="utf-8").splitlines()]
    assert atoms[-1]["record_type"] == "workflow_atom"
    assert atoms[-1]["task_id"] == "TASK-0001"
    assert atoms[-1]["fact"] == "Focused pytest passed for workflow linter."
    assert atoms[-1]["result_ref"] == result.result_ref
    assert atoms[-1]["source_hash"] == result.source_hash

    scenario_text = scenario_path.read_text(encoding="utf-8")
    assert result.atom_id in scenario_text
    assert result.result_ref in scenario_text
    assert "Workflow linter verification completed" in scenario_text

    persona_text = persona_path.read_text(encoding="utf-8")
    assert "record_type: workflow_persona" in persona_text
    assert "Prefer exact command results" in persona_text

    canvas_text = canvas_path.read_text(encoding="utf-8")
    assert result.atom_id in canvas_text
    assert result.result_ref in canvas_text
    assert "TASK-0001" in canvas_text

    evidence_memory = json.loads(evidence_memory_path.read_text(encoding="utf-8"))
    assert evidence_memory["l0_raw_evidence_refs"][-1]["path"] == result.result_ref
    assert evidence_memory["canonical_artifacts"][-1]["evidence_refs"] == [f"raw-TASK-0001"]
    assert evidence_memory["l1_atoms"][-1]["canonical_artifact_refs"] == ["artifact-TASK-0001"]
    assert evidence_memory["l2_scenarios"][-1]["atom_refs"] == [result.atom_id]
    assert evidence_memory["l3_profile_claims"][-1]["evidence_refs"] == [f"raw-TASK-0001"]
    assert evidence_memory["mermaid_canvas_refs"][-1]["path"] == result.canvas_ref
    assert validate_evidence_memory_document(tmp_path, evidence_memory_path).record_count == 6


def test_pack_evidence_rejects_workspace_escape_for_task_id(tmp_path):
    raw_output = tmp_path / "raw.txt"
    raw_output.write_text("raw", encoding="utf-8")

    try:
        pack_evidence(
            root=tmp_path,
            task_id="../escape",
            input_path=raw_output,
            summary="Should fail.",
        )
    except ValueError as error:
        assert "task_id must contain" in str(error)
    else:
        raise AssertionError("pack_evidence should reject unsafe task ids")


def test_workflow_memory_record_uses_traceable_record_type(tmp_path):
    store = LongTermMemoryStore(tmp_path / "memory", backend_name="sqlite")
    try:
        record = store.add_workflow_memory(
            session_id="session-workflow",
            record_type="workflow_atom",
            summary="Workflow atom keeps a result ref.",
            payload={
                "task_id": "TASK-0001",
                "result_ref": ".agent/memory/refs/TASK-0001.md",
            },
            citations=[".agent/memory/refs/TASK-0001.md"],
        )

        stored = store.all_records()[0]
        assert record.id.startswith("workflow-")
        assert stored["source"] == "workflow_memory"
        assert stored["domain"] == "workflow"
        assert stored["category"] == "workflow/atom"
        assert stored["payload"]["record_type"] == "workflow_atom"
        assert stored["payload"]["result_ref"] == ".agent/memory/refs/TASK-0001.md"
        assert stored["citations"] == [".agent/memory/refs/TASK-0001.md"]
    finally:
        store.close()


def test_workflow_memory_record_rejects_untraceable_payload(tmp_path):
    store = LongTermMemoryStore(tmp_path / "memory", backend_name="sqlite")
    try:
        try:
            store.add_workflow_memory(
                session_id="session-workflow",
                record_type="workflow_atom",
                summary="Untraceable atom.",
                payload={"task_id": "TASK-0001"},
                citations=[],
            )
        except EvidenceMemoryValidationError as error:
            assert "raw evidence, canonical artifact, or lower-level trace" in str(error)
        else:
            raise AssertionError("workflow memory without trace refs should be rejected")
    finally:
        store.close()
