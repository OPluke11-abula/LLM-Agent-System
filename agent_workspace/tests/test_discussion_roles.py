import pytest

from agent_workspace.core.discussion_room import (
    DiscussionRoom,
    DiscussionRoleContract,
    VerifierVerdict,
)


def test_discussion_room_builds_twv_role_contracts(tmp_path):
    room = DiscussionRoom(workspace_path=str(tmp_path))

    contracts = room.build_role_contracts(
        [
            {"role": "architect", "name": "Planner"},
            {"role": "dev", "name": "Builder"},
            {"role": "qa", "name": "Auditor"},
        ]
    )

    assert [contract.runtime_role for contract in contracts] == ["thinker", "worker", "verifier"]
    assert contracts[0].name == "Planner"
    assert contracts[1].required is True
    assert contracts[2].verifier is True


def test_verifier_verdict_is_durable_and_serializable(tmp_path):
    room = DiscussionRoom(workspace_path=str(tmp_path))
    verdict = room.create_verifier_verdict(
        session_id="s1",
        topic="Add conductor telemetry",
        consensus_summary="Decision: accept after focused tests pass.",
        transcript=[
            {"agent": "Planner", "role": "architect", "content": "Plan is clear."},
            {"agent": "Auditor", "role": "qa", "content": "Decision: tests passed."},
        ],
        role_contracts=[
            DiscussionRoleContract(
                runtime_role="verifier",
                name="Auditor",
                source_role="qa",
                responsibility="Verify outcomes.",
                verifier=True,
            )
        ],
        risk_level="medium",
        approval_required=False,
        consensus_certificate=None,
    )

    dumped = verdict.to_dict()

    assert dumped["decision"] == "accept"
    assert dumped["durable"] is True
    assert dumped["verifier_role"] == "Auditor"
    assert "tests passed" in dumped["rationale"].lower()


def test_high_risk_verdict_requires_approval_or_consensus(tmp_path):
    room = DiscussionRoom(workspace_path=str(tmp_path))

    with pytest.raises(PermissionError, match="High-risk verifier verdict requires approval"):
        room.create_verifier_verdict(
            session_id="s1",
            topic="Rotate production credentials",
            consensus_summary="Decision: accept",
            transcript=[],
            role_contracts=[
                DiscussionRoleContract(
                    runtime_role="verifier",
                    name="Auditor",
                    source_role="qa",
                    responsibility="Verify outcomes.",
                    verifier=True,
                )
            ],
            risk_level="high",
            approval_required=False,
            consensus_certificate=None,
        )


def test_high_risk_verdict_accepts_consensus_certificate(tmp_path):
    room = DiscussionRoom(workspace_path=str(tmp_path))

    verdict = room.create_verifier_verdict(
        session_id="s1",
        topic="Rotate production credentials",
        consensus_summary="Decision: accept",
        transcript=[],
        role_contracts=[
            DiscussionRoleContract(
                runtime_role="verifier",
                name="Auditor",
                source_role="qa",
                responsibility="Verify outcomes.",
                verifier=True,
            )
        ],
        risk_level="high",
        approval_required=False,
        consensus_certificate={"payload_hash": "abc", "approvals": ["ceo", "cto", "dev"]},
    )

    assert verdict.decision == "accept"
    assert verdict.escalation == "consensus_certificate"
