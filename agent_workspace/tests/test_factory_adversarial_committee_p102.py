"""Unit and integration tests for Red/Blue Adversarial Committee Subsystem (Phase 102).

Validates adversarial debate turns, attack vector detection, defect mitigation defense,
quorum gating (approval vs rejection), and SelfHealingContract synthesis.
"""

from agent_workspace.core.factory import (
    AdversarialCommitteeEngine,
    AdversarialPersona,
    RefactoringTaskNode,
    RefactoringTaskType,
    VulnerabilitySeverity,
)


def test_adversarial_personas_and_turns():
    """Validates 5-turn adversarial debate sequence across Red and Blue teams."""
    engine = AdversarialCommitteeEngine()
    task = RefactoringTaskNode(
        node_id="task-async-1",
        title="Migrate audit_ledger I/O to async pipeline",
        task_type=RefactoringTaskType.ASYNC_MIGRATION,
        target_files=["agent_workspace/core/audit_ledger.py"],
        mutable_scope=["agent_workspace/core/audit_ledger.py"],
    )

    record = engine.conduct_debate(task)

    assert record.task_id == "task-async-1"
    assert len(record.turns) == 5

    speakers = [t.speaker for t in record.turns]
    assert speakers == [
        AdversarialPersona.REFACTORING_ARCHITECT,  # Turn 1 (Proposal)
        AdversarialPersona.SECURITY_ATTACKER,      # Turn 2 (Attack probes)
        AdversarialPersona.REGRESSION_GUARDIAN,    # Turn 3 (QA & assertions)
        AdversarialPersona.REFACTORING_ARCHITECT,  # Turn 4 (Defense & mitigations)
        AdversarialPersona.QUORUM_ARBITER,         # Turn 5 (Quorum evaluation)
    ]


def test_vulnerability_detection_and_mitigation():
    """Validates that Blue Team attack vectors are identified and defensively mitigated by Red Team."""
    engine = AdversarialCommitteeEngine()
    task = RefactoringTaskNode(
        node_id="task-async-2",
        title="Async Event Loop Refactoring",
        task_type=RefactoringTaskType.ASYNC_MIGRATION,
        target_files=["agent_workspace/core/engine.py"],
    )

    record = engine.conduct_debate(task)

    assert len(record.vulnerabilities_detected) >= 2
    vuln_categories = {v.category for v in record.vulnerabilities_detected}
    assert "CONCURRENCY_RACE" in vuln_categories
    assert "THREAD_SAFETY" in vuln_categories

    # All standard vulnerabilities should be mitigated in Turn 4
    for v in record.vulnerabilities_detected:
        assert v.resolved is True
        assert "Applied defensive hardening" in v.mitigation_plan


def test_quorum_acceptance_and_self_healing_contract():
    """Validates that a clean debate reaches Quorum and binds a SelfHealingContract."""
    engine = AdversarialCommitteeEngine(quorum_threshold=70.0)
    task = RefactoringTaskNode(
        node_id="task-mod-1",
        title="Decompose Monolithic Service",
        task_type=RefactoringTaskType.MODULARIZE,
        target_files=["agent_workspace/core/giant_service.py"],
    )

    record = engine.conduct_debate(task)

    assert record.consensus_score >= 70.0
    assert record.quorum_reached is True
    assert record.self_healing_contract is not None

    contract = record.self_healing_contract
    assert contract.task_id == "task-mod-1"
    assert len(contract.mandatory_test_assertions) >= 2
    assert any("pytest exit code == 0" in a for a in contract.mandatory_test_assertions)
    assert len(contract.rollback_triggers) >= 3
    assert contract.require_atomic_rollback is True


def test_quorum_rejection_on_unmitigated_critical_defect():
    """Ensures Quorum is strictly blocked when a CRITICAL vulnerability remains unmitigated."""
    engine = AdversarialCommitteeEngine(quorum_threshold=70.0)
    task = RefactoringTaskNode(
        node_id="task-vuln-critical",
        title="Subprocess Shell Execution Refactor",
        task_type=RefactoringTaskType.ASYNC_MIGRATION,
        target_files=["agent_workspace/core/subprocess_runner.py"],
    )

    # Force an unmitigated critical defect into the debate
    record = engine.conduct_debate(task, force_critical_defect=True)

    assert record.consensus_score <= 40.0
    assert record.quorum_reached is False
    assert record.self_healing_contract is None

    critical_vulns = [v for v in record.vulnerabilities_detected if v.severity == VulnerabilitySeverity.CRITICAL]
    assert len(critical_vulns) >= 1
    unresolved = [v for v in critical_vulns if not v.resolved]
    assert len(unresolved) >= 1
    assert unresolved[0].category == "ARBITRARY_CODE_EXECUTION"


def test_modularize_and_default_debate_types():
    """Validates attack vector diversity across different refactoring strategies."""
    engine = AdversarialCommitteeEngine()

    # Modularize strategy
    task_mod = RefactoringTaskNode(
        node_id="t-mod",
        title="Split Monolith",
        task_type=RefactoringTaskType.MODULARIZE,
        target_files=["monolith.py"],
    )
    rec_mod = engine.conduct_debate(task_mod)
    assert any(v.category == "INTERFACE_POLLUTION" for v in rec_mod.vulnerabilities_detected)

    # Type hardening strategy
    task_type = RefactoringTaskNode(
        node_id="t-type",
        title="Type Hardening",
        task_type=RefactoringTaskType.TYPE_HARDENING,
        target_files=["types.py"],
    )
    rec_type = engine.conduct_debate(task_type)
    assert any(v.category == "TYPED_FAILURES" for v in rec_type.vulnerabilities_detected)


def test_binding_to_refactoring_task_node():
    """Validates seamless binding of SelfHealingContract to RefactoringTaskNode."""
    engine = AdversarialCommitteeEngine()
    task = RefactoringTaskNode(
        node_id="task-bind-1",
        title="Bind Contract Verification",
        task_type=RefactoringTaskType.ASYNC_MIGRATION,
        target_files=["agent_workspace/core/ledger.py"],
    )

    record = engine.conduct_debate(task)
    assert record.quorum_reached is True

    # Bind contract to the task node
    task.self_healing_contract = record.self_healing_contract
    assert task.self_healing_contract is not None
    assert task.self_healing_contract.task_id == task.node_id
    assert task.self_healing_contract.max_healing_attempts == 3
