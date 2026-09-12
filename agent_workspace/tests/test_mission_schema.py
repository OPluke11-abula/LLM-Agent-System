from pathlib import Path

from agent_workspace.mission_schema import render_mission_schema, render_typescript_contracts


def test_checked_in_mission_schema_matches_generator() -> None:
    artifact = Path("schemas/mission_api.json")
    assert artifact.read_text(encoding="utf-8") == render_mission_schema()


def test_mission_schema_is_contract_derived() -> None:
    schema = render_mission_schema()
    assert '"artifact_version": 1' in schema
    assert "auto_merge_allowed" in schema
    assert "execution_policy" in schema
    assert "provider_call_limit" in schema


def test_checked_in_viewer_contracts_match_json_artifact() -> None:
    artifact = Path("schemas/mission_api.json")
    generated = Path("viewer/src/generated/missionContracts.ts")
    assert generated.read_text(encoding="utf-8") == render_typescript_contracts(
        artifact.read_text(encoding="utf-8")
    )


def test_viewer_contracts_preserve_safe_product_guards() -> None:
    generated = Path("viewer/src/generated/missionContracts.ts").read_text(encoding="utf-8")
    assert "auto_merge_allowed?: false" in generated
    assert "plan_digest: string" in generated
    assert "export type ApprovalGate" in generated
    assert "PlanApprovalSubject | ScopeApprovalSubject | DraftPRApprovalSubject" in generated
    assert " any " not in generated
