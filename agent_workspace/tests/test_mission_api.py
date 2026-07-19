from datetime import datetime, timezone
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_workspace.api import app
from agent_workspace.core.mission_contracts import EvidenceRecord, EvidenceType, ExecutionPlan, GateStatus, PlanTask
from agent_workspace.core.mission_model import Mission, MissionState
from agent_workspace.core.mission_store import MissionStore
from agent_workspace.core.product_contracts import MissionPolicy
from agent_workspace.routes.dependencies import API_KEYS
from agent_workspace.routes.missions import get_mission_store


def make_plan() -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-api-1",
        mission_id="mission-api-1",
        tasks=[PlanTask(task_id="task-1", title="Inspect", order=1)],
    )


def make_verifying_mission() -> Mission:
    return Mission(
        mission_id="mission-api-verifying",
        requirement="Verify a Mission.",
        repository_id="repo-1",
        current_state=MissionState.VERIFYING,
        execution_policy=MissionPolicy(),
        actor_id="actor-1",
    )


@pytest.fixture
def client(tmp_path: Path):
    store = MissionStore(tmp_path / "missions.db")
    app.dependency_overrides[get_mission_store] = lambda: store
    API_KEYS["mission-test-key"] = {
        "tenant": "tenant-1",
        "sub": "actor-1",
        "role": "tenant",
    }
    with TestClient(app) as test_client:
        yield test_client, store
    app.dependency_overrides.pop(get_mission_store, None)
    API_KEYS.pop("mission-test-key", None)


def auth_headers() -> dict[str, str]:
    return {"x-api-key": "mission-test-key"}


def auth_headers_for(key: str) -> dict[str, str]:
    return {"x-api-key": key}


def evidence_payload(evidence_id: str) -> dict[str, object]:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "evidence": {
            "evidence_id": evidence_id,
            "evidence_type": "test",
            "source": "pytest",
            "operation": "python -m pytest",
            "started_at": timestamp,
            "finished_at": timestamp,
            "exit_status": 0,
            "bounded_output_summary": "passed",
            "producing_agent": "spoofed-agent",
            "verification_status": "passed",
        },
        "expected_revision": 0,
    }


def test_mission_api_requires_authentication(client) -> None:
    test_client, _ = client
    response = test_client.get("/v1/missions")
    assert response.status_code == 401


def test_mission_test_fixture_is_disabled_by_default(client, monkeypatch) -> None:
    test_client, _ = client
    monkeypatch.delenv("LAS_ENABLE_MISSION_TEST_FIXTURE", raising=False)

    response = test_client.post(
        "/v1/missions/missing/test-fixture/evidence",
        headers=auth_headers(),
        json=evidence_payload("fixture-disabled"),
    )

    assert response.status_code == 404


def test_create_get_and_list_missions(client) -> None:
    test_client, _ = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={
            "requirement": "Create a protected Mission.",
            "repository_id": "repo-1",
            "actor_id": "spoofed-actor",
        },
    )

    assert created.status_code == 201
    mission_id = created.json()["mission_id"]
    assert created.json()["actor_id"] == "actor-1"
    assert test_client.get(f"/v1/missions/{mission_id}", headers=auth_headers()).status_code == 200
    listing = test_client.get("/v1/missions?limit=1", headers=auth_headers())
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1


def test_mission_api_exposes_backend_capabilities(client) -> None:
    test_client, _ = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={"requirement": "Read capabilities.", "repository_id": "repo-1"},
    )
    mission_id = created.json()["mission_id"]

    response = test_client.get(f"/v1/missions/{mission_id}/capabilities", headers=auth_headers())

    assert response.status_code == 200
    assert response.json()["current_state"] == "draft"
    assert "start_planning" in response.json()["allowed_events"]


def test_mission_api_transition_is_centralized_and_idempotent(client) -> None:
    test_client, _ = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={"requirement": "Transition a Mission.", "repository_id": "repo-1"},
    )
    mission_id = created.json()["mission_id"]
    body = {
        "event": "start_planning",
        "idempotency_key": "api-start",
        "expected_revision": 0,
    }

    first = test_client.post(
        f"/v1/missions/{mission_id}/transitions",
        headers=auth_headers(),
        json=body,
    )
    replay = test_client.post(
        f"/v1/missions/{mission_id}/transitions",
        headers=auth_headers(),
        json=body,
    )

    assert first.status_code == 200
    assert first.json()["mission"]["current_state"] == "planning"
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True


def test_mission_api_returns_conflict_and_invalid_transition_errors(client) -> None:
    test_client, _ = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={"requirement": "Check errors.", "repository_id": "repo-1"},
    )
    mission_id = created.json()["mission_id"]
    transition_path = f"/v1/missions/{mission_id}/transitions"
    first = test_client.post(
        transition_path,
        headers=auth_headers(),
        json={"event": "start_planning", "idempotency_key": "first", "expected_revision": 0},
    )
    stale = test_client.post(
        transition_path,
        headers=auth_headers(),
        json={"event": "submit_plan", "idempotency_key": "stale", "expected_revision": 0},
    )
    invalid = test_client.post(
        transition_path,
        headers=auth_headers(),
        json={"event": "start_planning", "idempotency_key": "invalid", "expected_revision": 1},
    )

    assert first.status_code == 200
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_revision"
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "invalid_transition"


def test_mission_api_binds_plan_approval_subject(client) -> None:
    test_client, store = client
    mission = Mission(
        mission_id="mission-api-1",
        requirement="Approve a plan.",
        repository_id="repo-1",
        execution_policy=MissionPolicy(),
        actor_id="actor-1",
    )
    store.create(mission)
    plan = make_plan()
    attached = test_client.put(
        f"/v1/missions/{mission.mission_id}/plan",
        headers=auth_headers(),
        json={"execution_plan": plan.model_dump(mode="json"), "expected_revision": 0},
    )
    assert attached.status_code == 200

    assert test_client.post(
        f"/v1/missions/{mission.mission_id}/transitions",
        headers=auth_headers(),
        json={"event": "start_planning", "idempotency_key": "plan-start", "expected_revision": 1},
    ).status_code == 200
    assert test_client.post(
        f"/v1/missions/{mission.mission_id}/transitions",
        headers=auth_headers(),
        json={"event": "submit_plan", "idempotency_key": "plan-submit", "expected_revision": 2},
    ).status_code == 200

    approval = test_client.post(
        f"/v1/missions/{mission.mission_id}/approvals",
        headers=auth_headers(),
        json={
            "gate_id": "plan-gate",
            "gate_type": "plan",
            "subject": {
                "kind": "plan",
                "plan_id": "plan-api-1",
                "plan_revision": 1,
                "plan_digest": plan.canonical_digest(),
            },
            "status": "approved",
            "idempotency_key": "plan-approval-1",
            "expected_revision": 3,
        },
    )
    assert approval.status_code == 200

    stale = test_client.post(
        f"/v1/missions/{mission.mission_id}/transitions",
        headers=auth_headers(),
        json={
            "event": "approve_plan",
            "idempotency_key": "stale-approval",
            "expected_revision": 4,
            "approval_subject": {
                "kind": "plan",
                "plan_id": "plan-api-1",
                "plan_revision": 2,
                "plan_digest": plan.canonical_digest(),
            },
        },
    )
    assert stale.status_code == 422
    assert stale.json()["code"] == "approval_subject_mismatch"


def test_mission_api_enforces_verification_completeness_and_pagination_bounds(client) -> None:
    test_client, store = client
    store.create(make_verifying_mission())
    incomplete = test_client.post(
        "/v1/missions/mission-api-verifying/transitions",
        headers=auth_headers(),
        json={"event": "complete_verification", "idempotency_key": "incomplete", "expected_revision": 0},
    )
    too_large = test_client.get("/v1/missions?limit=101", headers=auth_headers())

    assert incomplete.status_code == 422
    assert incomplete.json()["code"] == "verification_required"
    assert too_large.status_code == 422


def test_mission_api_exposes_audit_history_without_side_effect_routes(client) -> None:
    test_client, _ = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={"requirement": "Read audit history.", "repository_id": "repo-1"},
    )
    mission_id = created.json()["mission_id"]
    test_client.post(
        f"/v1/missions/{mission_id}/transitions",
        headers=auth_headers(),
        json={"event": "start_planning", "idempotency_key": "history-start", "expected_revision": 0},
    )

    history = test_client.get(f"/v1/missions/{mission_id}/transitions", headers=auth_headers())
    unknown = test_client.get("/v1/missions/missing/transitions", headers=auth_headers())

    assert history.status_code == 200
    assert len(history.json()["items"]) == 1
    assert unknown.status_code == 404


def test_mission_api_rejects_invalid_mutation_without_corrupting_prior_state(client) -> None:
    test_client, store = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={"requirement": "Protect evidence writes.", "repository_id": "repo-1"},
    )
    mission_id = created.json()["mission_id"]
    first = test_client.post(
        f"/v1/missions/{mission_id}/evidence",
        headers=auth_headers(),
        json=evidence_payload("evidence-api-1"),
    )
    duplicate = test_client.post(
        f"/v1/missions/{mission_id}/evidence",
        headers=auth_headers(),
        json={**evidence_payload("evidence-api-1"), "expected_revision": 1},
    )
    persisted = store.get(mission_id, owner_id="actor-1")

    assert first.status_code == 200
    assert duplicate.status_code == 422
    assert duplicate.json()["code"] == "duplicate_evidence"
    assert persisted is not None
    assert persisted.revision == 1
    assert len(persisted.evidence_records) == 1


def test_mission_api_isolates_two_authenticated_owners(client) -> None:
    test_client, _ = client
    API_KEYS["mission-owner-two-key"] = {
        "tenant": "tenant-2",
        "sub": "actor-2",
        "role": "tenant",
    }
    try:
        created = test_client.post(
            "/v1/missions",
            headers=auth_headers(),
            json={"requirement": "Owner isolation.", "repository_id": "repo-1"},
        )
        mission_id = created.json()["mission_id"]
        hidden_get = test_client.get(
            f"/v1/missions/{mission_id}",
            headers=auth_headers_for("mission-owner-two-key"),
        )
        hidden_list = test_client.get(
            "/v1/missions",
            headers=auth_headers_for("mission-owner-two-key"),
        )
        hidden_transition = test_client.post(
            f"/v1/missions/{mission_id}/transitions",
            headers=auth_headers_for("mission-owner-two-key"),
            json={
                "event": "start_planning",
                "idempotency_key": "owner-two-transition",
                "expected_revision": 0,
            },
        )

        assert hidden_get.status_code == 404
        assert hidden_list.json()["items"] == []
        assert hidden_transition.status_code == 404
    finally:
        API_KEYS.pop("mission-owner-two-key", None)


def test_mission_api_maps_corrupt_payload_to_server_error(client) -> None:
    test_client, store = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={"requirement": "Corruption mapping.", "repository_id": "repo-1"},
    )
    mission_id = created.json()["mission_id"]
    with sqlite3.connect(store.database_path) as connection:
        connection.execute(
            "UPDATE missions SET payload = ? WHERE mission_id = ?",
            ("{not-json}", mission_id),
        )
        connection.commit()

    response = test_client.get(f"/v1/missions/{mission_id}", headers=auth_headers())

    assert response.status_code == 500
    assert response.json()["code"] == "corrupt_mission_payload"
    assert "payload" not in response.json()["message"].lower()


def test_mission_api_system_capabilities_reports_safe_readiness(client) -> None:
    test_client, _ = client

    response = test_client.get("/v1/system/capabilities", headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["api_reachable"] is True
    assert body["authentication_valid"] is True
    assert body["mission_store_available"] is True
    assert body["schema_compatible"] is True
    assert body["agent_execution"] == "not_implemented"
    assert body["draft_pr_delivery"] == "not_implemented"
    assert "api_key" not in str(body).lower()


def test_mission_api_rejects_stale_idempotent_plan_replay(client) -> None:
    test_client, store = client
    mission = Mission(
        mission_id="mission-stale-plan",
        requirement="Stale plan replay.",
        repository_id="repo-1",
        execution_policy=MissionPolicy(),
        actor_id="actor-1",
    )
    store.create(mission)
    plan = ExecutionPlan(
        plan_id="plan-stale-replay",
        mission_id=mission.mission_id,
        tasks=[PlanTask(task_id="task-1", title="Inspect", order=1)],
    )
    path = f"/v1/missions/{mission.mission_id}/plan"
    first = test_client.put(path, headers=auth_headers(), json={"execution_plan": plan.model_dump(mode="json"), "expected_revision": 0})
    replay_with_stale_revision = test_client.put(path, headers=auth_headers(), json={"execution_plan": plan.model_dump(mode="json"), "expected_revision": 0})

    assert first.status_code == 200
    assert replay_with_stale_revision.status_code == 409
    assert replay_with_stale_revision.json()["code"] == "stale_revision"


def test_mission_api_maps_conflicting_approval_replay_to_conflict(client) -> None:
    test_client, _ = client
    created = test_client.post(
        "/v1/missions",
        headers=auth_headers(),
        json={"requirement": "Conflicting approval.", "repository_id": "repo-1"},
    )
    mission_id = created.json()["mission_id"]
    subject = {"kind": "scope_expansion", "scope_request_id": "scope-1"}
    body = {"gate_id": "scope-gate-1", "gate_type": "scope_expansion", "subject": subject, "status": "approved", "evidence_refs": [], "idempotency_key": "approval-1", "expected_revision": 0}
    first = test_client.post(f"/v1/missions/{mission_id}/approvals", headers=auth_headers(), json=body)
    conflict = test_client.post(f"/v1/missions/{mission_id}/approvals", headers=auth_headers(), json={**body, "gate_id": "scope-gate-2", "status": "rejected", "idempotency_key": "approval-2", "expected_revision": 1})

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "immutable_decision_conflict"
