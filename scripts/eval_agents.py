from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_workspace.core.discussion_room import DiscussionRoom


def _load_fixtures(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_eval(fixtures_path: Path, workspace_path: Path) -> dict[str, Any]:
    room = DiscussionRoom(workspace_path=str(workspace_path))
    fixtures = _load_fixtures(fixtures_path)
    results = []

    for fixture in fixtures:
        started = time.perf_counter()
        role_contracts = room.build_role_contracts(fixture["agents"])
        unresolved_risks: list[str] = []
        try:
            verdict = room.create_verifier_verdict(
                session_id=fixture["id"],
                topic=fixture["topic"],
                consensus_summary=fixture["consensus_summary"],
                transcript=fixture.get("transcript", []),
                role_contracts=role_contracts,
                risk_level=fixture.get("risk_level", "medium"),
                approval_required=fixture.get("approval_required", False),
                consensus_certificate=fixture.get("consensus_certificate"),
            )
            verifier_outcome = verdict.to_dict()
            completed = verdict.decision == fixture.get("expected_decision", verdict.decision)
        except Exception as exc:
            verifier_outcome = {"decision": "error", "error": str(exc)}
            completed = False
            unresolved_risks.append(str(exc))

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        results.append(
            {
                "id": fixture["id"],
                "completed": completed,
                "cost_usd": 0.0,
                "latency_ms": elapsed_ms,
                "tool_use": [],
                "verifier_outcome": verifier_outcome,
                "unresolved_risk": unresolved_risks,
            }
        )

    passed = sum(1 for result in results if result["completed"])
    return {
        "suite": "agent_golden_smoke",
        "fixtures": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic LAS agent golden smoke evals.")
    parser.add_argument("--fixtures", default="scripts/agent_eval_fixtures.json")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report = run_eval(Path(args.fixtures), Path(args.workspace))
    output = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
