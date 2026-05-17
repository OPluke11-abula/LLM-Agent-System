"""Tool Manifest generator for LAS — PAP skill contract auto-sync.

This module bridges LAS runtime tool discovery (Pydantic reflection) with the
Portable Agent Protocol (PAP) skill contract format.  It can:

1. **Generate** a machine-readable ``tool_manifest.json`` from the live
   ``AgentEngine`` tool registry.
2. **Sync** the PAP ``.agent/skills/`` directory and ``.agent/skills.md``
   registry to stay in lockstep with the runtime tools.
3. **Validate** that every runtime tool has a matching PAP contract and
   vice-versa.

Usage::

    # CLI
    python agent_workspace/tool_manifest.py generate
    python agent_workspace/tool_manifest.py sync
    python agent_workspace/tool_manifest.py validate

    # API (imported)
    from tool_manifest import ToolManifest
    manifest = ToolManifest.from_engine(engine)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace)

from core.engine import AgentEngine

MANIFEST_VERSION = "1.0.0"
MANIFEST_FILENAME = "tool_manifest.json"


# ---------------------------------------------------------------------------
#  Data model
# ---------------------------------------------------------------------------

@dataclass
class ToolEntry:
    """A single tool in the manifest."""
    name: str
    description: str
    module: str
    function: str
    input_schema: dict[str, Any]
    wants_context: bool = False
    pap_contract: str | None = None  # path to .agent/skills/<name>.md


@dataclass
class ToolManifest:
    """Complete tool manifest for the workspace."""
    manifest_version: str = MANIFEST_VERSION
    generated_at: str = ""
    workspace: str = ""
    tool_count: int = 0
    tools: list[ToolEntry] = field(default_factory=list)

    @classmethod
    def from_engine(cls, engine: AgentEngine) -> "ToolManifest":
        """Build a manifest from a live AgentEngine instance."""
        tools: list[ToolEntry] = []
        project_root = Path(engine.workspace_path).parent

        for name, tool_info in engine.tools_registry.items():
            func = tool_info["function"]
            module_file = getattr(sys.modules.get(func.__module__), "__file__", None)
            if module_file:
                try:
                    module_rel = str(Path(module_file).relative_to(project_root))
                except ValueError:
                    module_rel = module_file
            else:
                module_rel = func.__module__

            # Check for matching PAP contract
            pap_path = project_root / ".agent" / "skills" / f"{name}.md"
            pap_contract = str(pap_path.relative_to(project_root)) if pap_path.exists() else None

            schema = tool_info["schema"].copy()
            schema.pop("title", None)

            tools.append(ToolEntry(
                name=name,
                description=(tool_info["description"] or "").strip(),
                module=module_rel.replace("\\", "/"),
                function=func.__name__,
                input_schema=schema,
                wants_context=tool_info["wants_context"],
                pap_contract=pap_contract.replace("\\", "/") if pap_contract else None,
            ))

        return cls(
            manifest_version=MANIFEST_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            workspace=str(engine.workspace_path),
            tool_count=len(tools),
            tools=tools,
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)

    def save(self, path: str | Path | None = None) -> Path:
        if path is None:
            path = Path(workspace) / MANIFEST_FILENAME
        else:
            path = Path(path)
        path.write_text(self.to_json(), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
#  PAP Sync — generate .agent/skills/<name>.md from runtime tools
# ---------------------------------------------------------------------------

_PAP_SKILL_TEMPLATE = """---
name: "{name}"
description: "{description}"
version: "1.0.0"
author: "LAS Tool Manifest Auto-Sync"
---

# {name}

> **PAP Skill Contract**: This document defines the exact execution boundaries, inputs, and outputs for this skill. AI agents MUST strictly adhere to these specifications.

## 1. Purpose (目的)

{description}

## 2. Required Inputs (輸入參數)

{inputs_section}

## 3. Expected Outputs (預期輸出)

- **Success Format**: Plain text result string.
- **Error Format**: String prefixed with `Error:`.

## 4. Execution Boundaries & Safety (執行邊界與安全)

> [!WARNING]
> **Safety Constraints:**
> - This contract is auto-generated from runtime Pydantic reflection.
> - Review and adjust safety notes before production use.

## 5. Runtime Mapping

- Module: `{module}`
- Function: `{function}`
- Argument model: Pydantic `BaseModel` (see input schema)
- Wants context: `{wants_context}`

---
*Generated by: LAS Tool Manifest Auto-Sync*
"""


def _render_inputs(schema: dict[str, Any]) -> str:
    """Render input_schema properties as markdown list."""
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    lines = []
    for param_name, param_info in props.items():
        param_type = param_info.get("type", "any")
        req_label = "**Required**" if param_name in required else "Optional"
        desc = param_info.get("description", "")
        lines.append(f"- `{param_name}` ({param_type}, {req_label}): {desc}")
    return "\n".join(lines) if lines else "- _(no parameters)_"


def sync_pap_contracts(manifest: ToolManifest, project_root: Path) -> list[str]:
    """Create or update .agent/skills/<name>.md for each tool.

    Returns list of paths that were written.
    """
    skills_dir = project_root / ".agent" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for tool in manifest.tools:
        contract_path = skills_dir / f"{tool.name}.md"
        # Only write if missing — don't overwrite hand-edited contracts
        if contract_path.exists():
            continue
        content = _PAP_SKILL_TEMPLATE.format(
            name=tool.name,
            description=tool.description,
            inputs_section=_render_inputs(tool.input_schema),
            module=tool.module,
            function=tool.function,
            wants_context=tool.wants_context,
        )
        contract_path.write_text(content.strip() + "\n", encoding="utf-8")
        written.append(str(contract_path.relative_to(project_root)))

    return written


def sync_skills_md(manifest: ToolManifest, project_root: Path) -> None:
    """Regenerate .agent/skills.md registry from manifest."""
    lines = [
        "# Skills Entry Point",
        "",
        "This file is the PAP-facing skill registry for LAS.",
        "",
        "LAS discovers executable tools from `agent_workspace/skills/*.py` through",
        "Pydantic model reflection. This document maps those runtime tools to portable",
        "skill contracts.",
        "",
        "## Runtime Skill Modules",
        "",
        "| Skill | Runtime module | Function | Contract |",
        "| --- | --- | --- | --- |",
    ]
    for tool in manifest.tools:
        contract = tool.pap_contract or f".agent/skills/{tool.name}.md"
        lines.append(f"| `{tool.name}` | `{tool.module}` | `{tool.function}` | `{contract}` |")

    lines.extend([
        "",
        "## Adding New Skills",
        "",
        "1. Add or update a Python module under `agent_workspace/skills/`.",
        "2. Expose a function whose first argument is a Pydantic `BaseModel`.",
        "3. Let `AgentEngine` reflect the tool schema.",
        "4. Run `python agent_workspace/tool_manifest.py sync` to auto-generate contracts.",
        "5. Review and refine the generated `.agent/skills/<skill_name>.md`.",
        "",
        "## 中文說明",
        "",
        "LAS 的可執行工具仍由 `agent_workspace/skills/*.py` 提供，並透過 Pydantic",
        "自動反射成 tool schema。執行 `tool_manifest.py sync` 即可自動產生 PAP skill",
        "contract 並更新本檔案。",
        "",
    ])
    (project_root / ".agent" / "skills.md").write_text("\n".join(lines), encoding="utf-8")


def sync_agent_md_tools(manifest: ToolManifest, project_root: Path) -> None:
    """Update the tools: list in .agent/agent.md frontmatter."""
    agent_md = project_root / ".agent" / "agent.md"
    if not agent_md.exists():
        return

    content = agent_md.read_text(encoding="utf-8")
    # Find and replace the tools: block in YAML frontmatter
    import re
    tool_names = [tool.name for tool in manifest.tools]
    new_tools_block = "tools:\n" + "\n".join(f"  - {name}" for name in tool_names)

    # Match existing tools block in frontmatter
    pattern = r"tools:\n(?:  - .+\n)+"
    if re.search(pattern, content):
        content = re.sub(pattern, new_tools_block + "\n", content)
        agent_md.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
#  Validation
# ---------------------------------------------------------------------------

def validate(manifest: ToolManifest, project_root: Path) -> list[str]:
    """Check consistency between runtime tools and PAP contracts.

    Returns list of warning strings (empty = all good).
    """
    warnings: list[str] = []
    skills_dir = project_root / ".agent" / "skills"

    # 1. Every runtime tool should have a PAP contract
    for tool in manifest.tools:
        contract = skills_dir / f"{tool.name}.md"
        if not contract.exists():
            warnings.append(f"MISSING_CONTRACT: tool '{tool.name}' has no .agent/skills/{tool.name}.md")

    # 2. Every PAP contract should have a matching runtime tool
    tool_names = {t.name for t in manifest.tools}
    if skills_dir.exists():
        for md_file in skills_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue  # skip templates
            skill_name = md_file.stem
            if skill_name not in tool_names:
                warnings.append(f"ORPHAN_CONTRACT: .agent/skills/{md_file.name} has no matching runtime tool")

    return warnings


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LAS Tool Manifest — PAP Skill Contract Manager")
    parser.add_argument("command", choices=["generate", "sync", "validate"],
                        help="generate: write tool_manifest.json | sync: generate + update PAP contracts | validate: check consistency")
    parser.add_argument("--output", type=str, help="Output path for tool_manifest.json")
    args = parser.parse_args()

    engine = AgentEngine(workspace_path=workspace)
    manifest = ToolManifest.from_engine(engine)
    project_root = Path(workspace).parent

    if args.command == "generate":
        out = manifest.save(args.output)
        print(f"✅ tool_manifest.json written to {out}")
        print(f"   {manifest.tool_count} tool(s) registered")

    elif args.command == "sync":
        out = manifest.save(args.output)
        print(f"✅ tool_manifest.json written to {out}")

        written = sync_pap_contracts(manifest, project_root)
        if written:
            print(f"✅ Created {len(written)} new PAP contract(s):")
            for w in written:
                print(f"   + {w}")
        else:
            print("✅ All PAP contracts already exist")

        sync_skills_md(manifest, project_root)
        print("✅ .agent/skills.md updated")

        sync_agent_md_tools(manifest, project_root)
        print("✅ .agent/agent.md tools list synced")

    elif args.command == "validate":
        warnings = validate(manifest, project_root)
        if warnings:
            print(f"⚠ {len(warnings)} issue(s) found:")
            for w in warnings:
                print(f"   {w}")
        else:
            print(f"✅ All {manifest.tool_count} tool(s) have matching PAP contracts")

    # Always print manifest summary
    print(f"\nManifest ({manifest.manifest_version}):")
    for tool in manifest.tools:
        contract_status = "✅" if tool.pap_contract else "❌"
        print(f"  {contract_status} {tool.name}: {tool.description[:60]}")


if __name__ == "__main__":
    main()
