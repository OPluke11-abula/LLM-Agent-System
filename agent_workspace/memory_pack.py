"""Explicit evidence memory packing for LAS workflow artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

workspace_parent = Path(__file__).resolve().parents[1]
if str(workspace_parent) not in sys.path:
    sys.path.insert(0, str(workspace_parent))

from agent_workspace.long_term_memory import LongTermMemoryStore


TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class MemoryPackResult:
    task_id: str
    atom_id: str
    result_ref: str
    canvas_ref: str
    source_hash: str


def pack_evidence(
    *,
    root: str | Path,
    task_id: str,
    input_path: str | Path,
    summary: str | None = None,
    scenario: str | None = None,
    persona: str | None = None,
    store_long_term: bool = False,
    session_id: str = "workflow-memory",
) -> MemoryPackResult:
    """Pack one explicit evidence file into traceable workflow memory files."""

    if not TASK_ID_PATTERN.match(task_id):
        raise ValueError("task_id must contain only letters, numbers, underscores, and hyphens")

    root_path = Path(root).resolve()
    source_path = Path(input_path).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"input file does not exist: {input_path}")

    raw_text = source_path.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    fact = summary or f"Evidence packed for {task_id} from {source_path.name}."
    atom_id = f"atom-{hashlib.sha256((task_id + source_hash + fact).encode('utf-8')).hexdigest()[:12]}"

    memory_root = root_path / ".agent" / "memory"
    refs_dir = memory_root / "refs"
    canvases_dir = memory_root / "canvases"
    scenarios_dir = memory_root / "l2-scenarios"
    for directory in (refs_dir, canvases_dir, scenarios_dir):
        directory.mkdir(parents=True, exist_ok=True)

    ref_path = refs_dir / f"{task_id}.md"
    atom_path = memory_root / "l1-atoms.jsonl"
    scenario_path = scenarios_dir / f"{task_id}.md"
    persona_path = memory_root / "l3-persona.md"
    canvas_path = canvases_dir / f"{task_id}.mmd"

    ref_path.write_text(raw_text, encoding="utf-8")

    result_ref = _relative_posix(root_path, ref_path)
    canvas_ref = _relative_posix(root_path, canvas_path)
    atom_record = {
        "id": atom_id,
        "record_type": "workflow_atom",
        "task_id": task_id,
        "fact": fact,
        "result_ref": result_ref,
        "source_path": _relative_or_absolute(root_path, source_path),
        "source_hash": source_hash,
    }
    _upsert_jsonl(atom_path, atom_record)

    scenario_text = scenario or f"Evidence memory pack for {task_id}."
    scenario_path.write_text(
        "\n".join(
            [
                f"# Scenario: {task_id}",
                "",
                "record_type: workflow_scenario",
                f"atom_ref: {atom_id}",
                f"result_ref: {result_ref}",
                "",
                scenario_text,
                "",
            ]
        ),
        encoding="utf-8",
    )

    if persona:
        persona_path.write_text(
            "\n".join(
                [
                    "# Workflow Persona",
                    "",
                    "record_type: workflow_persona",
                    "",
                    persona,
                    "",
                ]
            ),
            encoding="utf-8",
        )

    canvas_path.write_text(
        "\n".join(
            [
                "graph TD",
                f"  task_{_node_id(task_id)}[\"{task_id}\"] --> atom_{_node_id(atom_id)}[\"{atom_id}\"]",
                f"  atom_{_node_id(atom_id)} --> ref_{_node_id(source_hash[:12])}[\"{result_ref}\"]",
                "",
            ]
        ),
        encoding="utf-8",
    )

    if store_long_term:
        store = LongTermMemoryStore(root_path / "memory", backend_name="sqlite")
        try:
            store.add_workflow_memory(
                session_id=session_id,
                record_type="evidence_ref",
                summary=f"Evidence ref for {task_id}: {result_ref}",
                payload={"task_id": task_id, "result_ref": result_ref, "source_hash": source_hash},
                citations=[result_ref],
            )
            store.add_workflow_memory(
                session_id=session_id,
                record_type="workflow_atom",
                summary=fact,
                payload=atom_record,
                citations=[result_ref],
            )
        finally:
            store.close()

    return MemoryPackResult(
        task_id=task_id,
        atom_id=atom_id,
        result_ref=result_ref,
        canvas_ref=canvas_ref,
        source_hash=source_hash,
    )


def _upsert_jsonl(path: Path, record: dict[str, str]) -> None:
    records: list[dict[str, str]] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing = json.loads(line)
            if existing.get("id") != record["id"]:
                records.append(existing)
    records.append(record)
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records),
        encoding="utf-8",
    )


def _relative_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _relative_or_absolute(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _node_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pack explicit evidence into LAS workflow memory files.")
    parser.add_argument("--root", default=".", help="Workspace root. Defaults to current directory.")
    parser.add_argument("--task", required=True, help="Task id for memory refs, for example TASK-0001.")
    parser.add_argument("--input", required=True, help="Raw evidence file to copy into .agent/memory/refs/.")
    parser.add_argument("--summary", help="Traceable L1 atom fact. Defaults to a generated summary.")
    parser.add_argument("--scenario", help="Optional L2 scenario text.")
    parser.add_argument("--persona", help="Optional L3 stable preference/profile text.")
    parser.add_argument("--store-long-term", action="store_true", help="Also store traceable records in LongTermMemoryStore.")
    parser.add_argument("--session", default="workflow-memory", help="Session id for optional long-term memory storage.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    result = pack_evidence(
        root=args.root,
        task_id=args.task,
        input_path=args.input,
        summary=args.summary,
        scenario=args.scenario,
        persona=args.persona,
        store_long_term=args.store_long_term,
        session_id=args.session,
    )
    print(
        f"Packed evidence for {result.task_id}: "
        f"atom={result.atom_id}, ref={result.result_ref}, canvas={result.canvas_ref}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
