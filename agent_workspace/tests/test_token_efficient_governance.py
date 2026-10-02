from pathlib import Path
from typing import Final

import pytest
from pydantic import ValidationError

from agent_workspace.core.token_efficient_profile import TokenEfficientProfile, VerificationProfile


WORKFLOW_ROOT: Final[Path] = Path(__file__).resolve().parents[2] / ".agent" / "knowledge_base" / "workflows"


@pytest.mark.parametrize("verification_profile", ["focused", "surface", "full", "release"])
def test_profile_selection_accepts_supported_verification_profiles(verification_profile: VerificationProfile):
    profile = TokenEfficientProfile(verification_profile=verification_profile)

    assert profile.verification_profile == verification_profile


def test_profile_selection_rejects_unknown_verification_profile():
    with pytest.raises(ValidationError):
        TokenEfficientProfile.model_validate({"verification_profile": "blocking"})


def test_structural_lookup_contract_requires_bounded_broad_read_justification():
    workflow = (WORKFLOW_ROOT / "structural-lookup-first.md").read_text(encoding="utf-8")

    for marker in ("Broad read:", "Reason:", "Needed to answer:", "Bound:", "Follow-up:"):
        assert marker in workflow


def test_verification_profile_contract_maps_all_profiles_to_live_commands():
    workflow = (WORKFLOW_ROOT / "verification-profiles.md").read_text(encoding="utf-8")

    for profile in ("`focused`", "`surface`", "`full`", "`release`"):
        assert profile in workflow
    for command in ("pytest", "npm.cmd --prefix viewer run build", "verify:ui:screenshots", "git diff --check", "scripts/verify.cmd"):
        assert command in workflow


def test_rollout_contract_keeps_token_mode_advisory_and_report_only():
    workflow = (WORKFLOW_ROOT / "token-efficient-rollout.md").read_text(encoding="utf-8")

    assert "advisory-only" in workflow
    assert "`report_only=true`" in workflow
    assert "`trimming_applied=false`" in workflow
    assert "does not archive, delete, compact, trim, or mutate session state" in workflow
