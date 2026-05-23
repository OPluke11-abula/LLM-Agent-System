"""Unified Operations Developer CLI toolbelt for FindAi Studio LLM Agent System (LAS)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

# Add workspace directory to path
workspace = os.path.dirname(os.path.abspath(__file__))
if workspace not in sys.path:
    sys.path.insert(0, workspace)

try:
    from core.engine import AgentEngine
    from core.router import AgentRouter
    from core.workflow_engine import WorkflowEngine
    from long_term_memory import LongTermMemoryStore
    from pap_validate import validate as run_pap_validate
except ImportError:
    # Fallback to local imports if needed
    from agent_workspace.core.engine import AgentEngine
    from agent_workspace.core.router import AgentRouter
    from agent_workspace.core.workflow_engine import WorkflowEngine
    from agent_workspace.long_term_memory import LongTermMemoryStore
    from agent_workspace.pap_validate import validate as run_pap_validate

def handle_list_skills(args):
    """List all registered tools including local and global overrides."""
    engine = AgentEngine(workspace_path=workspace)
    router = AgentRouter(engine, session_id="cli-session")
    skills = router.list_skills()
    
    if not skills:
        print("No registered skills found.")
        return
        
    print(f"{'Skill ID':<25} | {'Version':<8} | {'Description':<50}")
    print("-" * 90)
    for skill in skills:
        name = skill.get("id", "unknown")
        version = skill.get("version", "1.0.0")
        desc = skill.get("description", "").strip().splitlines()[0] if skill.get("description") else ""
        desc_trunc = desc[:50] + "..." if len(desc) > 50 else desc
        print(f"{name:<25} | {version:<8} | {desc_trunc:<50}")

def handle_describe_skill(args):
    """Describe the specified skill contract."""
    engine = AgentEngine(workspace_path=workspace)
    router = AgentRouter(engine, session_id="cli-session")
    try:
        desc = router.describe_skill(args.describe_skill)
        print(yaml.safe_dump(desc, allow_unicode=True, sort_keys=False))
    except FileNotFoundError as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

def handle_validate(args):
    """Run structural gate validation checks."""
    project_root = Path(workspace).parent
    try:
        run_pap_validate(project_root)
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        sys.exit(1)

def handle_memory_read(args):
    """Read a memory record by key."""
    memory_dir = args.memory_dir or os.path.join(workspace, "memory")
    store = LongTermMemoryStore(memory_dir, backend_name=args.backend)
    session = args.session or "global_session"
    
    record = store._backend.read(session, args.memory_read)
    if not record:
        # Search all records across all sessions if not found in target session
        for r in store.all_records():
            if r.get("id") == args.memory_read:
                record = r
                break
                
    if record:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print(f"Memory record '{args.memory_read}' not found.", file=sys.stderr)
        sys.exit(1)

def handle_memory_write(args):
    """Write a custom memory record by key and value."""
    key = args.memory_write[0]
    value = args.memory_write[1]
    
    memory_dir = args.memory_dir or os.path.join(workspace, "memory")
    store = LongTermMemoryStore(memory_dir, backend_name=args.backend)
    session = args.session or "global_session"
    
    domain = "semantic" if key.startswith("sem-") else ("preference" if key.startswith("pref-") else "episodic")
    
    record = {
        "id": key,
        "session_id": session,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "cli_write",
        "source_hash": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "summary": value,
        "keywords": LongTermMemoryStore._keywords(value),
        "message_count": 0,
        "payload": {"text": value},
        "domain": domain,
        "confidence": 1.0,
        "privacy_level": "project"
    }
    
    store._backend.write(session, key, record)
    print(f"Successfully wrote memory record '{key}' under session '{session}'.")

def handle_run_workflow(args):
    """Run or resume an asynchronous workflow."""
    workflow_id = args.run_workflow
    session = args.session or f"wf-session-{workflow_id}"
    
    engine = AgentEngine(workspace_path=workspace)
    workflow_engine = WorkflowEngine(engine)
    
    print(f"Executing workflow '{workflow_id}' (Session ID: {session})...")
    try:
        results = asyncio.run(workflow_engine.execute(
            workflow_id=workflow_id,
            session_id=session,
            resume=args.resume
        ))
        print("Workflow executed successfully!")
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Workflow execution failed: {e}", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Operations Developer CLI toolbelt for LAS.")
    
    # Global flags
    parser.add_argument("--session", type=str, help="Isolation session ID for memory or workflow runs.")
    parser.add_argument("--memory-dir", type=str, help="Override long-term memory directory.")
    parser.add_argument("--backend", type=str, default="sqlite", help="Memory backend (sqlite, redis, file).")
    
    group = parser.add_mutually_exclusive_group(required=True)
    
    # Flags
    group.add_argument("--list-skills", action="store_true", help="List all registered tools.")
    group.add_argument("--describe-skill", type=str, metavar="SKILL_ID", help="Display details for a specific skill contract.")
    group.add_argument("--validate", action="store_true", help="Run PAP structural validation.")
    group.add_argument("--memory-read", type=str, metavar="KEY", help="Read memory record by key.")
    group.add_argument("--memory-write", nargs=2, metavar=("KEY", "VALUE"), help="Write custom memory record.")
    group.add_argument("--run-workflow", type=str, metavar="WORKFLOW_ID", help="Execute or resume declarative workflow.")
    
    parser.add_argument("--resume", action="store_true", help="Resume workflow execution from last failed step.")
    
    args = parser.parse_args()
    
    if args.list_skills:
        handle_list_skills(args)
    elif args.describe_skill:
        handle_describe_skill(args)
    elif args.validate:
        handle_validate(args)
    elif args.memory_read:
        handle_memory_read(args)
    elif args.memory_write:
        handle_memory_write(args)
    elif args.run_workflow:
        handle_run_workflow(args)

if __name__ == "__main__":
    main()
