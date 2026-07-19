from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends

from agent_workspace.core.mission_api_contracts import MissionActor, MissionSystemCapabilities
from agent_workspace.core.mission_store import MissionStoreError
from agent_workspace.core.product_contracts import SCHEMA_VERSION
from agent_workspace.routes.dependencies import (
    get_account_manager,
    get_workspace,
    load_llm_config,
    required_env_for_provider,
)
from agent_workspace.routes.missions import get_mission_store, require_mission_actor


router = APIRouter(prefix="/v1/system", tags=["system"])
VIEWER_EXPECTED_SCHEMA_VERSION = SCHEMA_VERSION


def _provider_configuration() -> Literal["configured", "not_configured", "unavailable"]:
    try:
        account = get_account_manager().get_active_account()
        if account is not None and get_account_manager().resolve_api_key(account):
            return "configured"
        config = load_llm_config()
        provider = config.get("provider")
        if not isinstance(provider, str):
            return "unavailable"
        required_env = required_env_for_provider(provider)
        if required_env is None:
            return "unavailable"
        return "configured" if os.environ.get(required_env) else "not_configured"
    except (OSError, TypeError, ValueError, KeyError):
        return "unavailable"


def _store_available(actor: MissionActor) -> bool:
    try:
        get_mission_store().list(limit=1, offset=0, owner_id=actor.actor_id)
        return True
    except MissionStoreError:
        return False


@router.get("/capabilities", response_model=MissionSystemCapabilities)
def get_system_capabilities(actor: MissionActor = Depends(require_mission_actor)) -> MissionSystemCapabilities:
    workspace_root = Path(get_workspace())
    store_available = _store_available(actor)
    return MissionSystemCapabilities(
        api_reachable=True,
        authentication_valid=True,
        workspace_root_available=workspace_root.is_dir(),
        mission_store_available=store_available,
        contract_schema_version=SCHEMA_VERSION,
        viewer_expected_schema_version=VIEWER_EXPECTED_SCHEMA_VERSION,
        schema_compatible=SCHEMA_VERSION == VIEWER_EXPECTED_SCHEMA_VERSION,
        provider_configuration=_provider_configuration(),
        git_integration="not_implemented",
        github_integration="not_implemented",
        repository_inspection="not_implemented",
        agent_execution="not_implemented",
        draft_pr_delivery="not_implemented",
    )
