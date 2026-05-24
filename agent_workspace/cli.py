"""Unified Operations Developer CLI toolbelt for FindAi Studio LLM Agent System (LAS)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
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

SEMVER_REGEX = re.compile(r"^v?\d+\.\d+\.\d+(?:-[\w.]+)?(?:\+[\w.]+)?$")

def handle_init(args):
    """Bootstrap a standard skeletal .agent/ folder structure."""
    target_dir = Path(args.path).resolve()
    agent_dir = target_dir / ".agent"
    
    subdirs = [
        agent_dir,
        agent_dir / "skills",
        agent_dir / "prompts",
        agent_dir / "memory",
        agent_dir / "workflows",
        agent_dir / "knowledge_base",
        agent_dir / "memory" / "episodic",
        agent_dir / "memory" / "semantic",
        agent_dir / "memory" / "handoff",
        agent_dir / "workflows" / "runs",
    ]
    
    files = {
        agent_dir / "agent.md": """---
protocol_version: "1.0.0"
min_runtime_version: "0.1.0"
name: skeletal-agent
version: "1.0.0"
purpose: >
  Standard skeletal agent bootstrapped via the LAS CLI toolbelt.
description: >
  This agent serves as a foundation for implementing PAP-compliant agent workflows.
language: en
authorization_level: interactive-approval
use_case_tags:
  - general
  - template
tools:
  - calculate
---

# Agent Identity Manifest

This is the standard agent identity manifest bootstrapped by the LAS CLI.
""",
        agent_dir / "skills.md": """---
schema_version: "1.0.0"
---

# Skills Entry Point

This file catalogs PAP-facing skills for the agent.

## Runtime Skill Modules

| Skill | Runtime module | Function | Contract |
| --- | --- | --- | --- |
| `calculate` | `agent_workspace/skills/math.py` | `calculate` | `.agent/skills/calculate.md` |
""",
        agent_dir / "agent_tasks.md": """# PAP Agent Task Queue (English Master Edition)
>
> **Protocol**: Portable Agent Protocol (PAP) v0.1.0  
> **Format**: PAP Task Contract v1  
> **Status legend**: `[ ]` pending · `[~]` in-progress · `[x]` done · `[!]` blocked

---

## 🛠️ PHASE 0 — Foundation

### 0-01 Initialize Workspace
- [x] Create skeletal `.agent/` structure
- [ ] Implement initial domain modeling
- [ ] Scaffold custom skills
""",
        agent_dir / "README.md": """# PAP Workspace Overview

Welcome to your Portable Agent Protocol (PAP) workspace.
This directory contains standard schemas, contracts, memory logs, and declarative workflows.
""",
        agent_dir / "prompts.md": """# Prompts Entry Point

This file tracks active prompt templates for the agent runtime.
""",
        agent_dir / "memory.md": """# Memory Entry Point

This file details the episodic, semantic, and handoff memory structures.
""",
        agent_dir / "workflows.md": """# Workflows Entry Point

This file defines the declarative workflow graphs for this agent.
""",
        agent_dir / "skills" / "calculate.md": """---
id: calculate
description: Perform math calculations.
version: 1.0.0
inputs:
  expression:
    type: string
    required: true
    description: Math expression to evaluate.
outputs:
  success: Plain text result string.
  error: String prefixed with Error.
safety_notes:
  - Safe local sandbox evaluation.
author: LAS Tool Manifest Auto-Sync
---

# calculate
"""
    }
    
    if args.dry_run:
        print("Dry run active: proposed bootstrapping operations:")
        for s in subdirs:
            print(f"  [Directory] {s.relative_to(target_dir)}")
        for f in files.keys():
            print(f"  [File]      {f.relative_to(target_dir)}")
        return
        
    for s in subdirs:
        s.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {s}")
        
    for f_path, content in files.items():
        if not f_path.exists():
            f_path.write_text(content, encoding="utf-8")
            print(f"Created file: {f_path}")
        else:
            print(f"File already exists (skipped): {f_path}")
            
    print(f"Successfully bootstrapped .agent/ at {agent_dir}")

def handle_lint(args):
    """Statically lint the PAP workspace contracts."""
    project_root = Path(args.path).resolve()
    agent_dir = project_root / ".agent"
    
    errors = []
    warnings = []
    
    # 1. Check agent.md existence and keys
    agent_md = agent_dir / "agent.md"
    if not agent_md.is_file():
        errors.append("CRITICAL: .agent/agent.md is missing")
        print("\n".join(errors))
        sys.exit(1)
        
    try:
        raw_agent = agent_md.read_text(encoding="utf-8")
        from core.engine import AgentEngine
        frontmatter, _ = AgentEngine._split_frontmatter(raw_agent)
    except Exception as e:
        errors.append(f"CRITICAL: Failed to parse .agent/agent.md frontmatter: {e}")
        print("\n".join(errors))
        sys.exit(1)
        
    REQUIRED_KEYS = [
        "protocol_version",
        "min_runtime_version",
        "name",
        "version",
        "purpose",
        "language",
        "authorization_level",
        "use_case_tags",
        "tools"
    ]
    for key in REQUIRED_KEYS:
        if key not in frontmatter:
            errors.append(f"ERROR: agent.md is missing required manifest key '{key}'")
            
    # 2. Check semver formats
    for key in ["protocol_version", "min_runtime_version", "version"]:
        if key in frontmatter:
            val = str(frontmatter[key])
            if not SEMVER_REGEX.match(val):
                errors.append(f"ERROR: agent.md '{key}' has invalid semver format: '{val}'")
                
    # 3. Live skill contract alignment
    tools = frontmatter.get("tools", [])
    if not isinstance(tools, list):
        errors.append("ERROR: agent.md 'tools' key must be a list of tool names")
        tools = []
        
    skills_dir = agent_dir / "skills"
    
    for tool in tools:
        contract_path = skills_dir / f"{tool}.md"
        if not contract_path.is_file():
            errors.append(f"ERROR: Missing skill contract for tool '{tool}' at .agent/skills/{tool}.md")
            continue
            
        try:
            raw_contract = contract_path.read_text(encoding="utf-8")
            c_fm, _ = AgentEngine._split_frontmatter(raw_contract)
            
            required_contract_keys = ["id", "description", "inputs", "outputs", "safety_notes", "version"]
            for ck in required_contract_keys:
                if ck not in c_fm:
                    errors.append(f"ERROR: Contract skills/{tool}.md is missing required key '{ck}'")
            
            if c_fm.get("id") != tool:
                errors.append(f"ERROR: Contract skills/{tool}.md ID '{c_fm.get('id')}' does not match tool name '{tool}'")
                
            c_ver = c_fm.get("version")
            if c_ver and not SEMVER_REGEX.match(str(c_ver)):
                errors.append(f"ERROR: Contract skills/{tool}.md version '{c_ver}' is not valid semver")
        except Exception as e:
            errors.append(f"ERROR: Failed to parse skills/{tool}.md: {e}")
            
    if skills_dir.is_dir():
        for md_file in skills_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue
            if md_file.stem not in tools:
                warnings.append(f"WARNING: Orphan contract '.agent/skills/{md_file.name}' not declared in agent.md tools list")
                
    # 4. Workflow reference validation
    workflows_dir = agent_dir / "workflows"
    if workflows_dir.is_dir():
        for wf_file in workflows_dir.glob("*.md"):
            if wf_file.name.startswith("_"):
                continue
            try:
                raw_wf = wf_file.read_text(encoding="utf-8")
                wf_fm, _ = AgentEngine._split_frontmatter(raw_wf)
                
                wf_id = wf_fm.get("id", wf_file.stem)
                steps = wf_fm.get("steps", [])
                if not isinstance(steps, list):
                    errors.append(f"ERROR: Workflow '{wf_id}' 'steps' must be a list")
                    continue
                    
                step_ids = {s.get("step_id") for s in steps if isinstance(s, dict) and s.get("step_id")}
                
                for idx, step in enumerate(steps):
                    if not isinstance(step, dict):
                        errors.append(f"ERROR: Workflow '{wf_id}' step at index {idx} is not a valid dictionary")
                        continue
                        
                    step_id = step.get("step_id")
                    skill_id = step.get("skill_id")
                    
                    if not step_id:
                        errors.append(f"ERROR: Workflow '{wf_id}' step at index {idx} is missing 'step_id'")
                        continue
                        
                    if not skill_id:
                        errors.append(f"ERROR: Workflow '{wf_id}' step '{step_id}' is missing 'skill_id'")
                        continue
                        
                    if skill_id not in tools:
                        errors.append(f"ERROR: Workflow '{wf_id}' step '{step_id}' references undeclared tool/skill '{skill_id}'")
                        
                    next_step = step.get("next_step")
                    if next_step and not ("{{" in next_step and "}}" in next_step):
                        if next_step not in step_ids:
                            errors.append(f"ERROR: Workflow '{wf_id}' step '{step_id}' references non-existent next_step '{next_step}'")
            except Exception as e:
                errors.append(f"ERROR: Failed to parse workflow file '{wf_file.name}': {e}")
                
    # 5. Handle --fix if requested
    if args.fix:
        print("Auto-fix option requested. Resolving parity issues...")
        try:
            import tool_manifest
            engine = AgentEngine(workspace_path=str(project_root / "agent_workspace"))
            manifest = tool_manifest.ToolManifest.from_engine(engine)
            written = tool_manifest.sync_pap_contracts(manifest, project_root)
            tool_manifest.sync_skills_md(manifest, project_root)
            tool_manifest.sync_agent_md_tools(manifest, project_root)
            if written:
                print(f"Fixed: Scaffolded {len(written)} missing skill contracts.")
            
            # Remove orphan warnings from list and disk
            for warn in list(warnings):
                if "Orphan contract" in warn:
                    parts = warn.split("'")
                    if len(parts) >= 2:
                        orphan_rel = parts[1]
                        orphan_abs = project_root / orphan_rel
                        if orphan_abs.is_file():
                            orphan_abs.unlink()
                            print(f"Fixed: Removed orphan contract '{orphan_rel}'")
                            warnings.remove(warn)
            print("Parity alignment synchronized successfully.")
        except Exception as e:
            print(f"Auto-fix encountered an error: {e}", file=sys.stderr)
            
    if warnings:
        print(f"\nLint found {len(warnings)} non-blocking warning(s):")
        for warn in warnings:
            print(f"  {warn}")
            
    if errors:
        print(f"\nLint failed with {len(errors)} blocking error(s):")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("PAP Workspace contracts are 100% healthy and aligned! (0 blocking errors)")

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
    group.add_argument("--init", action="store_true", help="Bootstrap a standard skeletal .agent/ folder structure.")
    group.add_argument("--lint", action="store_true", help="Statically check the .agent/ workspace integrity.")
    
    parser.add_argument("--resume", action="store_true", help="Resume workflow execution from last failed step.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate init subcommand without creating files.")
    parser.add_argument("--fix", action="store_true", help="Automatically correct linting anomalies if possible.")
    parser.add_argument("path", nargs="?", default=".", help="Target path for bootstrap or lint (for init/lint subcommands).")
    
    # Map command words "init" and "lint" to flags for backward compatibility and DX
    sys_args = sys.argv[1:]
    if "init" in sys_args:
        idx = sys_args.index("init")
        sys_args[idx] = "--init"
    elif "lint" in sys_args:
        idx = sys_args.index("lint")
        sys_args[idx] = "--lint"
        
    args = parser.parse_args(sys_args)
    
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
    elif args.init:
        handle_init(args)
    elif args.lint:
        handle_lint(args)

if __name__ == "__main__":
    main()
