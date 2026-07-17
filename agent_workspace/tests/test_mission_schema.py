from pathlib import Path

from agent_workspace.mission_schema import render_mission_schema


def test_checked_in_mission_schema_matches_generator() -> None:
    artifact = Path("schemas/mission_api.json")
    assert artifact.read_text(encoding="utf-8") == render_mission_schema()


def test_mission_schema_is_contract_derived() -> None:
    schema = render_mission_schema()
    assert '"artifact_version": 1' in schema
    assert "auto_merge_allowed" in schema
    assert "execution_policy" in schema
    assert "provider_call_limit" in schema
