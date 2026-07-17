"""Render the deterministic machine-readable Mission API schema artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import BaseModel

from agent_workspace.core.mission_api_contracts import (
    ApprovalRecordRequest,
    EvidenceRecordRequest,
    MissionCreateRequest,
    MissionTransitionAPIRequest,
    MissionTransitionResponse,
    PlanAttachRequest,
    VerificationRecordRequest,
)
from agent_workspace.core.mission_contracts import ExecutionPlan
from agent_workspace.core.mission_model import Mission


SCHEMA_ARTIFACT_VERSION = 1
_SCHEMA_MODELS: tuple[type[BaseModel], ...] = (
    Mission,
    ExecutionPlan,
    MissionCreateRequest,
    MissionTransitionAPIRequest,
    MissionTransitionResponse,
    PlanAttachRequest,
    ApprovalRecordRequest,
    EvidenceRecordRequest,
    VerificationRecordRequest,
)


def render_mission_schema() -> str:
    """Return the canonical JSON schema bundle for Mission contracts."""
    models = {
        model.__name__: model.model_json_schema(ref_template="#/$defs/{model}")
        for model in _SCHEMA_MODELS
    }
    bundle = {
        "artifact_version": SCHEMA_ARTIFACT_VERSION,
        "models": models,
    }
    return json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> None:
    """Write the schema artifact to the repository or a supplied path."""
    if len(sys.argv) > 2:
        raise SystemExit("usage: python -m agent_workspace.mission_schema [output-path]")
    target = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1] / "schemas" / "mission_api.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_mission_schema(), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
