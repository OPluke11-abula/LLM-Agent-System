import sqlite3
from pathlib import Path

import pytest

from agent_workspace.core.mission_model import (
    Mission,
    MissionEvent,
    MissionState,
    TransitionRequest,
)
from agent_workspace.core.mission_state_machine import MissionTransitionError
from agent_workspace.core.product_contracts import MissionPolicy
from agent_workspace.core.mission_store import (
    MAX_MISSION_PAGE_SIZE,
    MissionStore,
    MissionStoreConflictError,
    MissionStoreCorruptionError,
    MissionStoreValidationError,
)


def make_mission() -> Mission:
    return Mission(
        mission_id="mission-store-1",
        requirement="Persist a Mission.",
        repository_id="repo-1",
        execution_policy=MissionPolicy(),
        actor_id="developer-1",
    )


def request(event: MissionEvent, key: str) -> TransitionRequest:
    return TransitionRequest(
        event=event,
        actor_id="developer-1",
        idempotency_key=key,
    )


def test_create_get_and_reload_after_store_reconstruction(tmp_path: Path) -> None:
    database = tmp_path / "missions.db"
    original = make_mission()

    with MissionStore(database) as store:
        assert store.create(original) == original

    with MissionStore(database) as reloaded:
        assert reloaded.get(original.mission_id) == original


def test_duplicate_create_fails_closed(tmp_path: Path) -> None:
    with MissionStore(tmp_path / "missions.db") as store:
        mission = make_mission()
        store.create(mission)

        with pytest.raises(MissionStoreConflictError) as error:
            store.create(mission)

    assert error.value.code == "duplicate_mission"


def test_save_uses_monotonic_expected_revision(tmp_path: Path) -> None:
    with MissionStore(tmp_path / "missions.db") as store:
        mission = store.create(make_mission())
        updated = mission.model_copy(update={"requirement": "Updated requirement."})
        saved = store.save(updated, expected_revision=0)

        assert saved.revision == 1
        assert store.get(saved.mission_id) == saved

        with pytest.raises(MissionStoreConflictError) as error:
            store.save(updated, expected_revision=0)

    assert error.value.code == "stale_revision"


def test_transition_atomically_persists_state_revision_and_audit(tmp_path: Path) -> None:
    with MissionStore(tmp_path / "missions.db") as store:
        mission = store.create(make_mission())
        result = store.append_transition(
            mission.mission_id,
            request(MissionEvent.START_PLANNING, "start-planning"),
        )
        persisted = store.get(mission.mission_id)

    assert result.mission.current_state is MissionState.PLANNING
    assert persisted is not None
    assert persisted.revision == 1
    assert persisted.transition_audit == (result.audit,)


def test_idempotency_replay_survives_process_restart(tmp_path: Path) -> None:
    database = tmp_path / "missions.db"
    mission = make_mission()
    transition_request = request(MissionEvent.START_PLANNING, "restart-safe-key")

    with MissionStore(database) as store:
        store.create(mission)
        first = store.append_transition(mission.mission_id, transition_request)

    with MissionStore(database) as reloaded:
        replay = reloaded.append_transition(mission.mission_id, transition_request)
        with pytest.raises(MissionStoreConflictError) as error:
            reloaded.append_transition(
                mission.mission_id,
                request(MissionEvent.CANCEL, "restart-safe-key"),
            )

    assert first.audit == replay.audit
    assert replay.replayed is True
    assert error.value.code == "idempotency_conflict"


def test_list_is_bounded_and_deterministically_paginated(tmp_path: Path) -> None:
    with MissionStore(tmp_path / "missions.db") as store:
        for suffix in ("a", "b", "c"):
            store.create(make_mission().model_copy(update={"mission_id": f"mission-{suffix}"}))
        page = store.list(limit=2, offset=0)

        assert tuple(item.mission_id for item in page.items) == ("mission-a", "mission-b")
        assert page.next_offset == 2

        with pytest.raises(MissionStoreValidationError):
            store.list(limit=MAX_MISSION_PAGE_SIZE + 1, offset=0)


def test_unsupported_schema_version_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "missions.db"
    with MissionStore(database) as store:
        store.create(make_mission())

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE missions SET schema_version = ? WHERE mission_id = ?",
            ("99.0", "mission-store-1"),
        )
        connection.commit()

    with MissionStore(database) as store:
        with pytest.raises(MissionStoreCorruptionError):
            store.get("mission-store-1")


def test_transition_rolls_back_after_simulated_failure(tmp_path: Path) -> None:
    database = tmp_path / "missions.db"
    with MissionStore(database) as store:
        mission = store.create(make_mission())
        store.before_commit = lambda: (_ for _ in ()).throw(RuntimeError("simulated failure"))

        with pytest.raises(RuntimeError, match="simulated failure"):
            store.append_transition(mission.mission_id, request(MissionEvent.START_PLANNING, "rollback"))

        persisted = store.get(mission.mission_id)

    assert persisted is not None
    assert persisted.current_state is MissionState.DRAFT
    assert persisted.revision == 0
    assert persisted.transition_audit == ()


def test_store_payload_contains_no_machine_path_or_secret_fields(tmp_path: Path) -> None:
    database = tmp_path / "missions.db"
    with MissionStore(database) as store:
        store.create(make_mission())

    with sqlite3.connect(database) as connection:
        payload = connection.execute(
            "SELECT payload FROM missions WHERE mission_id = ?",
            ("mission-store-1",),
        ).fetchone()[0]

    assert "local_path" not in payload
    assert "secret" not in payload.lower()
