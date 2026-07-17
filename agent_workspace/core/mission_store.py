"""Durable local SQLite boundary for the immutable Mission aggregate."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Callable, Final

from pydantic import ValidationError

from agent_workspace.core.mission_model import (
    Mission,
    MissionTransitionAudit,
    TransitionRequest,
)
from agent_workspace.core.mission_state_machine import (
    MissionStateMachine,
    MissionTransitionError,
    TransitionResult,
)
from agent_workspace.core.mission_contracts import serialize_contract
from agent_workspace.core.product_contracts import ContractModel, MissionId, SCHEMA_VERSION


STORE_SCHEMA_VERSION: Final[int] = 1
MAX_MISSION_PAGE_SIZE: Final[int] = 100
Clock = Callable[[], datetime]


class MissionStoreError(RuntimeError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class MissionStoreConflictError(MissionStoreError):
    pass


class MissionStoreCorruptionError(MissionStoreError):
    pass


class MissionStoreValidationError(MissionStoreError):
    pass


class MissionPage(ContractModel):
    items: tuple[Mission, ...]
    limit: int
    offset: int
    next_offset: int | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionStore:
    def __init__(
        self,
        database_path: str | Path,
        *,
        clock: Clock | None = None,
        machine: MissionStateMachine | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        if str(database_path) != ":memory:":
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock or _utc_now
        self._machine = machine or MissionStateMachine(clock=self._clock)
        self.before_commit: Callable[[], None] | None = None
        self._initialize()

    def __enter__(self) -> MissionStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path), timeout=30.0, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS mission_store_meta "
                "(schema_version INTEGER NOT NULL)"
            )
            metadata = connection.execute("SELECT schema_version FROM mission_store_meta").fetchone()
            if metadata is None:
                connection.execute(
                    "INSERT INTO mission_store_meta (schema_version) VALUES (?)",
                    (STORE_SCHEMA_VERSION,),
                )
            elif metadata["schema_version"] != STORE_SCHEMA_VERSION:
                raise MissionStoreCorruptionError(
                    "unsupported_store_schema",
                    "Mission store schema version is unsupported",
                )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS missions ("
                "mission_id TEXT PRIMARY KEY, schema_version TEXT NOT NULL, revision INTEGER NOT NULL, "
                "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS mission_transitions ("
                "mission_id TEXT NOT NULL, idempotency_key TEXT NOT NULL, event TEXT NOT NULL, "
                "audit TEXT NOT NULL, PRIMARY KEY (mission_id, idempotency_key), "
                "FOREIGN KEY (mission_id) REFERENCES missions(mission_id))"
            )
        finally:
            connection.close()

    @staticmethod
    def _payload(mission: Mission) -> str:
        return serialize_contract(mission)

    @staticmethod
    def _load_row(row: sqlite3.Row) -> Mission:
        if row["schema_version"] != SCHEMA_VERSION:
            raise MissionStoreCorruptionError(
                "unsupported_contract_schema",
                "Mission contract schema version is unsupported",
            )
        try:
            return Mission.model_validate_json(row["payload"])
        except (ValidationError, ValueError) as error:
            raise MissionStoreCorruptionError(
                "corrupt_mission_payload",
                "Stored Mission payload is invalid",
            ) from error

    def create(self, mission: Mission) -> Mission:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO missions "
                "(mission_id, schema_version, revision, created_at, updated_at, payload) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    mission.mission_id,
                    SCHEMA_VERSION,
                    mission.revision,
                    mission.created_at.isoformat(),
                    mission.updated_at.isoformat(),
                    self._payload(mission),
                ),
            )
            connection.commit()
            return mission
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise MissionStoreConflictError("duplicate_mission", "Mission already exists") from error
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, mission_id: MissionId) -> Mission | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT schema_version, payload FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            return None if row is None else self._load_row(row)
        finally:
            connection.close()

    def save(self, mission: Mission, *, expected_revision: int) -> Mission:
        if mission.revision != expected_revision:
            raise MissionStoreConflictError("stale_revision", "Mission revision does not match expected revision")
        updated = mission.model_copy(update={"revision": expected_revision + 1, "updated_at": self._clock()})
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE missions SET revision = ?, updated_at = ?, payload = ? "
                "WHERE mission_id = ? AND revision = ?",
                (
                    updated.revision,
                    updated.updated_at.isoformat(),
                    self._payload(updated),
                    updated.mission_id,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise MissionStoreConflictError("stale_revision", "Mission revision is stale")
            connection.commit()
            return updated
        except (sqlite3.Error, MissionStoreConflictError):
            connection.rollback()
            raise
        finally:
            connection.close()

    def list(self, *, limit: int = 50, offset: int = 0) -> MissionPage:
        if limit < 1 or limit > MAX_MISSION_PAGE_SIZE or offset < 0:
            raise MissionStoreValidationError("invalid_pagination", "Mission pagination bounds are invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT schema_version, payload FROM missions "
                "ORDER BY created_at ASC, mission_id ASC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            items = tuple(self._load_row(row) for row in rows)
            return MissionPage(
                items=items,
                limit=limit,
                offset=offset,
                next_offset=offset + limit if len(items) == limit else None,
            )
        finally:
            connection.close()

    def append_transition(
        self,
        mission_id: MissionId,
        request: TransitionRequest,
        *,
        expected_revision: int | None = None,
    ) -> TransitionResult:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT schema_version, revision, payload FROM missions WHERE mission_id = ?",
                (mission_id,),
            ).fetchone()
            if row is None:
                raise MissionStoreConflictError("mission_not_found", "Mission does not exist")
            mission = self._load_row(row)
            existing_row = connection.execute(
                "SELECT event, audit FROM mission_transitions WHERE mission_id = ? AND idempotency_key = ?",
                (mission_id, request.idempotency_key),
            ).fetchone()
            if existing_row is not None:
                try:
                    audit = MissionTransitionAudit.model_validate_json(existing_row["audit"])
                except (ValidationError, ValueError) as error:
                    raise MissionStoreCorruptionError(
                        "corrupt_transition_receipt",
                        "Stored transition receipt is invalid",
                    ) from error
                if audit.event is not request.event or audit.approval_subject != request.approval_subject:
                    raise MissionStoreConflictError(
                        "idempotency_conflict",
                        "Idempotency key was used for another event or subject",
                    )
                connection.commit()
                return TransitionResult(mission=mission, audit=audit, replayed=True)

            if expected_revision is not None and mission.revision != expected_revision:
                raise MissionStoreConflictError("stale_revision", "Mission revision is stale")

            result = self._machine.transition(mission, request)
            cursor = connection.execute(
                "UPDATE missions SET revision = ?, updated_at = ?, payload = ? "
                "WHERE mission_id = ? AND revision = ?",
                (
                    result.mission.revision,
                    result.mission.updated_at.isoformat(),
                    self._payload(result.mission),
                    mission_id,
                    mission.revision,
                ),
            )
            if cursor.rowcount != 1:
                raise MissionStoreConflictError("stale_revision", "Mission revision is stale")
            connection.execute(
                "INSERT INTO mission_transitions (mission_id, idempotency_key, event, audit) VALUES (?, ?, ?, ?)",
                (
                    mission_id,
                    request.idempotency_key,
                    request.event.value,
                    serialize_contract(result.audit),
                ),
            )
            if self.before_commit is not None:
                self.before_commit()
            connection.commit()
            return result
        except (sqlite3.Error, MissionStoreError, MissionTransitionError, RuntimeError):
            connection.rollback()
            raise
        finally:
            connection.close()

    def transition(self, mission_id: MissionId, request: TransitionRequest) -> TransitionResult:
        return self.append_transition(mission_id, request)
