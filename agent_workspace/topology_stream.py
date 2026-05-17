"""
External topology-aware stream runner for FindAi Studio.

This adapter preserves the engine boundary: it calls the public AgentRouter
stream API and mirrors yielded events into topology_state.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace)

from topology_bridge import TopologyEmitter, TopologyEvent


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("TopologyStream")


def default_topology_path() -> Path:
    workspace_dir = os.environ.get("AGENT_WORKSPACE_DIR")
    if workspace_dir:
        return Path(workspace_dir) / "topology_state.json"
    return Path(workspace).parent / "workspace" / "topology_state.json"


def session_payload(session_id: str, msg: str, status: str) -> dict[str, Any]:
    return {
        "name": session_id,
        "description": msg,
        "input": {"message": msg},
        "output": None,
        "rbac_role": "standard",
        "error_count": 0,
        "human_notes": "",
        "token_used": 0,
        "duration_ms": None,
        "status_reason": status,
    }


def tool_payload(name: str, arguments: dict[str, Any], result: Any = None, error_count: int = 0) -> dict[str, Any]:
    return {
        "name": name,
        "description": f"Tool call: {name}",
        "input": arguments,
        "output": result,
        "rbac_role": "standard",
        "error_count": error_count,
        "human_notes": "",
        "token_used": 0,
        "duration_ms": None,
    }


def emit_session_root(emitter: TopologyEmitter, root_id: str, msg: str, status: str) -> None:
    emitter.emit(
        TopologyEvent.create(
            session_id=emitter.session_id,
            node_id=root_id,
            node_type="session_root",
            status=status,
            payload=session_payload(emitter.session_id, msg, status),
        )
    )


async def run_stream(args: argparse.Namespace) -> int:
    session_id = args.session or "stream-session"
    msg = args.msg or "Hello"
    output_path = Path(args.output) if args.output else default_topology_path()
    emitter = TopologyEmitter(session_id=session_id, output_path=output_path)
    root_id = f"session-{session_id}"

    emit_session_root(emitter, root_id, msg, "running")

    if args.dry_run:
        emit_session_root(emitter, root_id, msg, "completed")
        print(f"topology_state.json written: {output_path}")
        return 0

    if not os.environ.get("GOOGLE_API_KEY"):
        emitter.emit(
            TopologyEvent.create(
                session_id=session_id,
                parent_node_id=root_id,
                node_type="error",
                edge_type="error",
                status="error",
                payload={
                    "name": "missing_google_api_key",
                    "description": "GOOGLE_API_KEY is not set.",
                    "input": {},
                    "output": None,
                    "rbac_role": "standard",
                    "error_count": 1,
                    "human_notes": "",
                    "token_used": 0,
                    "duration_ms": None,
                },
            )
        )
        emit_session_root(emitter, root_id, msg, "error")
        logger.error("GOOGLE_API_KEY not set.")
        return 1

    from core.engine import AgentEngine
    from core.router import AgentRouter

    engine = AgentEngine(workspace_path=workspace)
    router = AgentRouter(engine, session_id=session_id)
    active_tool_nodes: dict[str, str] = {}
    active_tool_args: dict[str, dict[str, Any]] = {}
    tool_failure_counts: dict[str, int] = {}

    print(f"\nUser: {msg}\nAgent: ", end="", flush=True)

    async for event in router.stream_agent_loop(msg):
        event_type = event.get("type")

        if event_type == "status":
            print(f"[{event['content']}]...", end="", flush=True)

        elif event_type == "tool_call":
            tool_name = str(event.get("name") or "unknown_tool")
            arguments = event.get("arguments") or {}
            node_id = f"tool-{event.get('id') or tool_name}-{len(active_tool_nodes) + 1}"
            active_tool_nodes[tool_name] = node_id
            active_tool_args[tool_name] = arguments
            emitter.emit(
                TopologyEvent.create(
                    session_id=session_id,
                    node_id=node_id,
                    parent_node_id=root_id,
                    node_type="tool_call",
                    edge_type="tool",
                    status="running",
                    payload=tool_payload(tool_name, arguments),
                )
            )
            print(f"\n[tool_call] {tool_name}({json.dumps(arguments, ensure_ascii=False)})", flush=True)

        elif event_type == "tool_result":
            tool_name = str(event.get("name") or "unknown_tool")
            result = event.get("result")
            node_id = active_tool_nodes.get(tool_name) or f"tool-{tool_name}"
            failed = isinstance(result, str) and (result.startswith("Error:") or "憭望?" in result)
            if failed:
                tool_failure_counts[tool_name] = tool_failure_counts.get(tool_name, 0) + 1
            else:
                tool_failure_counts[tool_name] = 0

            emitter.emit(
                TopologyEvent.create(
                    session_id=session_id,
                    node_id=node_id,
                    parent_node_id=root_id,
                    node_type="tool_call",
                    edge_type="error" if failed else "tool",
                    status="error" if failed else "completed",
                    payload=tool_payload(
                        tool_name,
                        active_tool_args.get(tool_name, {}),
                        result=result,
                        error_count=tool_failure_counts[tool_name],
                    ),
                )
            )

            if isinstance(result, str) and result.startswith("HANDOFF_TO:"):
                target_agent = result.split("HANDOFF_TO:", 1)[1].strip()
                emitter.emit(
                    TopologyEvent.create(
                        session_id=session_id,
                        parent_node_id=node_id,
                        node_type="handoff",
                        edge_type="handoff",
                        status="completed",
                        payload={
                            "name": target_agent,
                            "description": f"Handoff to {target_agent}",
                            "input": {"source_tool": tool_name},
                            "output": result,
                            "rbac_role": "standard",
                            "error_count": 0,
                            "human_notes": "",
                            "token_used": 0,
                            "duration_ms": None,
                        },
                    )
                )

            preview = str(result or "")[:50].replace("\n", " ")
            print(f"[tool_result] {preview}...\nAgent: ", end="", flush=True)

        elif event_type == "text_chunk":
            print(event["content"], end="", flush=True)

        elif event_type == "done":
            emit_session_root(emitter, root_id, msg, "completed")
            print("\n")

        elif event_type == "error":
            emitter.emit(
                TopologyEvent.create(
                    session_id=session_id,
                    parent_node_id=root_id,
                    node_type="error",
                    edge_type="error",
                    status="error",
                    payload={
                        "name": "stream_error",
                        "description": str(event.get("content") or ""),
                        "input": {},
                        "output": event.get("content"),
                        "rbac_role": "standard",
                        "error_count": 1,
                        "human_notes": "",
                        "token_used": 0,
                        "duration_ms": None,
                    },
                )
            )
            emit_session_root(emitter, root_id, msg, "error")
            print(f"\n[error] {event['content']}\n")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Topology-aware FindAi Studio stream runner")
    subparsers = parser.add_subparsers(dest="event", required=True)

    stream_parser = subparsers.add_parser("stream", help="Run agent stream and emit topology_state.json")
    stream_parser.add_argument("--msg", type=str, required=True, help="Message to send")
    stream_parser.add_argument("--session", type=str, help="Session ID for memory and topology isolation")
    stream_parser.add_argument("--output", type=str, help="Path to topology_state.json")
    stream_parser.add_argument("--dry-run", action="store_true", help="Write a session_root event without calling the LLM")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.event == "stream":
        return asyncio.run(run_stream(args))

    parser.error(f"Unknown event: {args.event}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
