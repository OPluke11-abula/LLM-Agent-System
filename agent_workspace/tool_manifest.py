"""Contract pipeline for LAS runtime tools and PAP skill documents.

This module bridges live tool reflection with the Portable Agent Protocol
workspace surface:

1. Generate a machine-readable tool manifest from ``AgentEngine``.
2. Create missing ``.agent/skills/<tool>.md`` contracts.
3. Regenerate ``.agent/skills.md`` from the live runtime registry.
4. Validate that runtime tools and PAP contracts stay in sync.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
import yaml
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

workspace = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, workspace)

try:
    from core.engine import AgentEngine
except ModuleNotFoundError as import_error:
    AgentEngine = None
    ENGINE_IMPORT_ERROR = import_error
else:
    ENGINE_IMPORT_ERROR = None


MANIFEST_VERSION = "1.0.0"
MANIFEST_FILENAME = "tool_manifest.json"


@dataclass
class ToolEntry:
    """One reflected runtime tool."""

    name: str
    description: str
    module: str
    function: str
    input_schema: dict[str, Any]
    wants_context: bool = False
    pap_contract: str | None = None


@dataclass
class ToolManifest:
    """Complete tool manifest for a LAS workspace."""

    manifest_version: str = MANIFEST_VERSION
    generated_at: str = ""
    workspace: str = ""
    tool_count: int = 0
    tools: list[ToolEntry] = field(default_factory=list)

    @classmethod
    def from_engine(cls, engine: Any) -> "ToolManifest":
        """Build a manifest from a live ``AgentEngine`` instance."""
        tools: list[ToolEntry] = []
        project_root = Path(engine.workspace_path).parent

        for name, tool_info in engine.tools_registry.items():
            if tool_info.get("is_global_skill"):
                continue  # Skip global skills from local manifest sync/validation
            func = tool_info["function"]
            module_file = getattr(sys.modules.get(func.__module__), "__file__", None)
            if module_file:
                try:
                    module_rel = str(Path(module_file).relative_to(project_root))
                except ValueError:
                    module_rel = module_file
            else:
                module_rel = func.__module__

            pap_path = project_root / ".agent" / "skills" / f"{name}.md"
            pap_contract = str(pap_path.relative_to(project_root)) if pap_path.exists() else None

            schema = tool_info["schema"].copy()
            schema.pop("title", None)

            tools.append(
                ToolEntry(
                    name=name,
                    description=(tool_info["description"] or "").strip(),
                    module=module_rel.replace("\\", "/"),
                    function=func.__name__,
                    input_schema=schema,
                    wants_context=tool_info["wants_context"],
                    pap_contract=pap_contract.replace("\\", "/") if pap_contract else None,
                )
            )

        return cls(
            manifest_version=MANIFEST_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            workspace=str(engine.workspace_path),
            tool_count=len(tools),
            tools=tools,
        )

    @classmethod
    def from_workspace_static(cls, workspace_path: str | Path) -> "ToolManifest":
        """Build a manifest by parsing skills/*.py without importing runtime deps."""
        workspace_path = Path(workspace_path)
        project_root = workspace_path.parent
        tools: list[ToolEntry] = []
        skills_dir = workspace_path / "skills"

        if skills_dir.is_dir():
            for skill_file in sorted(skills_dir.glob("*.py")):
                if skill_file.name == "__init__.py":
                    continue
                tools.extend(_parse_skill_file(skill_file, project_root))

        return cls(
            manifest_version=MANIFEST_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            workspace=str(workspace_path),
            tool_count=len(tools),
            tools=tools,
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=indent)

    def save(self, path: str | Path | None = None) -> Path:
        output_path = Path(path) if path is not None else Path(workspace) / MANIFEST_FILENAME
        output_path.write_text(self.to_json(), encoding="utf-8")
        return output_path


_PAP_SKILL_TEMPLATE = """---
name: "{name}"
description: "{description}"
version: "1.0.0"
author: "LAS Tool Manifest Auto-Sync"
---

# {name}

> **PAP Skill Contract**: This document defines the exact execution boundaries, inputs, and outputs for this skill.

## 1. Purpose

{description}

## 2. Required Inputs

{inputs_section}

## 3. Expected Outputs

- **Success format**: Plain text result string.
- **Error format**: String prefixed with `Error:`.

## 4. Execution Boundaries and Safety

- This contract is generated from runtime Pydantic reflection.
- Review and harden safety notes before production use.
- The runtime mapping below is authoritative for this generated contract.

## 5. Runtime Mapping

- Module: `{module}`
- Function: `{function}`
- Argument model: Pydantic `BaseModel` (see input schema)
- Wants context: `{wants_context}`

---
Generated by LAS Tool Manifest Auto-Sync.
"""


def _escape_frontmatter(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _render_inputs(schema: dict[str, Any]) -> str:
    """Render input_schema properties as a Markdown list."""
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    lines = []
    for param_name, param_info in props.items():
        param_type = param_info.get("type", "any")
        req_label = "**Required**" if param_name in required else "Optional"
        desc = param_info.get("description", "")
        lines.append(f"- `{param_name}` ({param_type}, {req_label}): {desc}")
    return "\n".join(lines) if lines else "- No parameters."


def _annotation_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _annotation_name(node.value)
    return ""


def _json_type(annotation: str) -> str:
    return {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "dict": "object",
        "list": "array",
    }.get(annotation, "string")


def _field_description(value: ast.AST | None) -> str:
    if not isinstance(value, ast.Call):
        return ""
    func_name = _annotation_name(value.func)
    if func_name != "Field":
        return ""
    for keyword in value.keywords:
        if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    return ""


def _parse_models(tree: ast.Module) -> dict[str, dict[str, Any]]:
    models: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(_annotation_name(base) == "BaseModel" for base in node.bases):
            continue

        properties: dict[str, Any] = {}
        required: list[str] = []
        for item in node.body:
            if not isinstance(item, ast.AnnAssign) or not isinstance(item.target, ast.Name):
                continue
            field_name = item.target.id
            annotation = _annotation_name(item.annotation)
            properties[field_name] = {
                "type": _json_type(annotation),
                "description": _field_description(item.value),
            }
            required.append(field_name)

        models[node.name] = {
            "type": "object",
            "properties": properties,
            "required": required,
        }
    return models


def _parse_skill_file(skill_file: Path, project_root: Path) -> list[ToolEntry]:
    raw = skill_file.read_text(encoding="utf-8")
    tree = ast.parse(raw, filename=str(skill_file))
    models = _parse_models(tree)
    entries: list[ToolEntry] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name.startswith("_"):
            continue
        if not node.args.args:
            continue
        first_arg = node.args.args[0]
        model_name = _annotation_name(first_arg.annotation)
        if model_name not in models:
            continue

        pap_path = project_root / ".agent" / "skills" / f"{node.name}.md"
        pap_contract = str(pap_path.relative_to(project_root)).replace("\\", "/") if pap_path.exists() else None
        module_rel = str(skill_file.relative_to(project_root)).replace("\\", "/")
        entries.append(
            ToolEntry(
                name=node.name,
                description=(ast.get_docstring(node) or "").strip(),
                module=module_rel,
                function=node.name,
                input_schema=models[model_name],
                wants_context=any(arg.arg == "context" for arg in node.args.args[1:]),
                pap_contract=pap_contract,
            )
        )

    return entries


def _extract_safety_notes(content: str) -> list[str]:
    lines = content.splitlines()
    notes = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            lower_head = stripped.lower()
            if "safety" in lower_head or "boundaries" in lower_head:
                in_section = True
            else:
                in_section = False
        elif in_section:
            if stripped.startswith("- "):
                note = stripped[2:].strip()
                if note and not note.startswith("This contract is generated") and not note.startswith("Review and harden") and not note.startswith("The runtime mapping below"):
                    notes.append(note)
            elif stripped.startswith("---") or (stripped.startswith("#") and not stripped.startswith("##")):
                in_section = False
    return notes


def sync_pap_contracts(manifest: ToolManifest, project_root: Path) -> list[str]:
    """Create or update .agent/skills/<name>.md files to the standardized schema format."""
    skills_dir = project_root / ".agent" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for tool in manifest.tools:
        contract_path = skills_dir / f"{tool.name}.md"
        
        # Extract inputs properties
        inputs_dict = {}
        props = tool.input_schema.get("properties", {})
        required_set = set(tool.input_schema.get("required", []))
        for param_name, param_info in props.items():
            inputs_dict[param_name] = {
                "type": param_info.get("type", "string"),
                "required": param_name in required_set,
                "description": param_info.get("description", "").strip()
            }

        outputs_dict = {
            "success": "Plain text result string.",
            "error": "String prefixed with Error:."
        }

        # Check existing safety notes
        existing_safety = []
        if contract_path.exists():
            try:
                existing_content = contract_path.read_text(encoding="utf-8")
                existing_safety = _extract_safety_notes(existing_content)
            except Exception:
                pass

        safety_notes_list = existing_safety if existing_safety else [
            "This contract is generated from runtime Pydantic reflection.",
            "Review and harden safety notes before production use."
        ]

        frontmatter = {
            "id": tool.name,
            "description": tool.description,
            "version": "1.0.0",
            "inputs": inputs_dict,
            "outputs": outputs_dict,
            "safety_notes": safety_notes_list,
            "author": "LAS Tool Manifest Auto-Sync"
        }
        
        frontmatter_yaml = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip()
        
        inputs_section = _render_inputs(tool.input_schema)
        safety_section = "\n".join(f"- {note}" for note in safety_notes_list)

        content = f"""---
{frontmatter_yaml}
---

# {tool.name}

> **PAP Skill Contract**: This document defines the exact execution boundaries, inputs, and outputs for this skill.

## 1. Purpose

{tool.description}

## 2. Required Inputs

{inputs_section}

## 3. Expected Outputs

- **Success format**: Plain text result string.
- **Error format**: String prefixed with `Error:`.

## 4. Execution Boundaries and Safety

{safety_section}

## 5. Runtime Mapping

- Module: `{tool.module}`
- Function: `{tool.function}`
- Argument model: Pydantic `BaseModel` (see input schema)
- Wants context: `{tool.wants_context}`

---
Generated by LAS Tool Manifest Auto-Sync.
"""
        # Read existing to see if it changed
        has_changed = True
        if contract_path.exists():
            try:
                old_content = contract_path.read_text(encoding="utf-8")
                if old_content.strip() == content.strip():
                    has_changed = False
            except Exception:
                pass
                
        if has_changed:
            contract_path.write_text(content.strip() + "\n", encoding="utf-8")
            written.append(str(contract_path.relative_to(project_root)))

    return written


def sync_skills_md(manifest: ToolManifest, project_root: Path) -> None:
    """Regenerate the PAP-facing skill registry."""
    lines = [
        "---",
        'schema_version: "1.0.0"',
        "---",
        "",
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

    lines.extend(
        [
            "",
            "## Adding New Skills",
            "",
            "1. Add or update a Python module under `agent_workspace/skills/`.",
            "2. Expose a function whose first argument is a Pydantic `BaseModel`.",
            "3. Let `AgentEngine` reflect the tool schema.",
            "4. Run `python agent_workspace/tool_manifest.py sync` to update contracts.",
            "5. Review and refine generated `.agent/skills/<skill_name>.md` files.",
            "",
            "## Contract Rule",
            "",
            "Runtime tools and PAP skill contracts must remain one-to-one. A tool without",
            "a contract is not AI-maintainable; a contract without a runtime tool is stale.",
            "Run `python agent_workspace/tool_manifest.py validate` before release.",
            "",
            "## 中文說明",
            "",
            "LAS 會從 `agent_workspace/skills/*.py` 反射可執行工具，並用本文件把 runtime",
            "工具對應到 `.agent/skills/*.md` 的 PAP contract。新增工具後請執行 `sync`，",
            "再人工檢查安全邊界與輸入輸出格式。",
            "",
        ]
    )
    (project_root / ".agent" / "skills.md").write_text("\n".join(lines), encoding="utf-8")


def sync_agent_md_tools(manifest: ToolManifest, project_root: Path) -> None:
    """Update the tools list in .agent/agent.md front matter."""
    agent_md = project_root / ".agent" / "agent.md"
    if not agent_md.exists():
        return

    content = agent_md.read_text(encoding="utf-8")
    tool_names = [tool.name for tool in manifest.tools]
    new_tools_block = "tools:\n" + "\n".join(f"  - {name}" for name in tool_names)
    pattern = r"tools:\n(?:  - .+\n)+"
    if re.search(pattern, content):
        content = re.sub(pattern, new_tools_block + "\n", content)
        agent_md.write_text(content, encoding="utf-8")


def validate(manifest: ToolManifest, project_root: Path) -> list[str]:
    """Check consistency between runtime tools and PAP contracts."""
    warnings: list[str] = []
    skills_dir = project_root / ".agent" / "skills"

    for tool in manifest.tools:
        contract = skills_dir / f"{tool.name}.md"
        if not contract.exists():
            warnings.append(f"MISSING_CONTRACT: tool '{tool.name}' has no .agent/skills/{tool.name}.md")
            continue

        # Parse and validate YAML front matter
        try:
            content = contract.read_text(encoding="utf-8")
            if not content.startswith("---"):
                warnings.append(f"INVALID_FRONTMATTER: .agent/skills/{tool.name}.md does not start with '---'")
                continue

            parts = content.split("---", 2)
            if len(parts) < 3:
                warnings.append(f"INVALID_FRONTMATTER: .agent/skills/{tool.name}.md is missing ending '---'")
                continue

            fm_raw = parts[1]
            fm = yaml.safe_load(fm_raw)
            if not isinstance(fm, dict):
                warnings.append(f"INVALID_FRONTMATTER: .agent/skills/{tool.name}.md front matter is not a YAML object/dictionary")
                continue

            # Check required keys
            required_keys = ["id", "description", "inputs", "outputs", "safety_notes", "version"]
            missing_keys = [k for k in required_keys if k not in fm]
            if missing_keys:
                warnings.append(f"MISSING_KEYS: .agent/skills/{tool.name}.md front matter is missing required keys: {', '.join(missing_keys)}")
                continue

            # Validate ID
            if fm["id"] != tool.name:
                warnings.append(f"INVALID_ID: .agent/skills/{tool.name}.md front matter 'id' must be '{tool.name}', got '{fm['id']}'")

            # Validate version
            if not isinstance(fm["version"], str) or not fm["version"].strip():
                warnings.append(f"INVALID_VERSION: .agent/skills/{tool.name}.md front matter 'version' must be a non-empty string")

            # Validate description
            if not isinstance(fm["description"], str) or not fm["description"].strip():
                warnings.append(f"INVALID_DESCRIPTION: .agent/skills/{tool.name}.md front matter 'description' must be a non-empty string")

            # Validate inputs
            if not isinstance(fm["inputs"], dict):
                warnings.append(f"INVALID_INPUTS: .agent/skills/{tool.name}.md front matter 'inputs' must be a dictionary")
            else:
                for param_name, param_info in fm["inputs"].items():
                    if not isinstance(param_info, dict):
                        warnings.append(f"INVALID_INPUT_PARAM: .agent/skills/{tool.name}.md front matter 'inputs.{param_name}' must be a dictionary")
                    else:
                        for sub_k in ["type", "required", "description"]:
                            if sub_k not in param_info:
                                warnings.append(f"MISSING_INPUT_PARAM_KEY: .agent/skills/{tool.name}.md front matter 'inputs.{param_name}' is missing required key '{sub_k}'")
                            elif sub_k == "required" and not isinstance(param_info[sub_k], bool):
                                warnings.append(f"INVALID_INPUT_PARAM_TYPE: .agent/skills/{tool.name}.md front matter 'inputs.{param_name}.required' must be a boolean")
                            elif sub_k != "required" and (not isinstance(param_info[sub_k], str) or not param_info[sub_k].strip()):
                                warnings.append(f"INVALID_INPUT_PARAM_TYPE: .agent/skills/{tool.name}.md front matter 'inputs.{param_name}.{sub_k}' must be a non-empty string")

            # Validate outputs
            if not isinstance(fm["outputs"], dict):
                warnings.append(f"INVALID_OUTPUTS: .agent/skills/{tool.name}.md front matter 'outputs' must be a dictionary")
            else:
                for ok in ["success", "error"]:
                    if ok not in fm["outputs"]:
                        warnings.append(f"MISSING_OUTPUT_KEY: .agent/skills/{tool.name}.md front matter 'outputs' is missing '{ok}'")
                    elif not isinstance(fm["outputs"][ok], str) or not fm["outputs"][ok].strip():
                        warnings.append(f"INVALID_OUTPUT_TYPE: .agent/skills/{tool.name}.md front matter 'outputs.{ok}' must be a non-empty string")

            # Validate safety_notes
            if not isinstance(fm["safety_notes"], list):
                warnings.append(f"INVALID_SAFETY_NOTES: .agent/skills/{tool.name}.md front matter 'safety_notes' must be a list of strings")
            else:
                for idx, note in enumerate(fm["safety_notes"]):
                    if not isinstance(note, str) or not note.strip():
                        warnings.append(f"INVALID_SAFETY_NOTE_ITEM: .agent/skills/{tool.name}.md front matter 'safety_notes[{idx}]' must be a non-empty string")

        except Exception as e:
            warnings.append(f"PARSE_ERROR: Failed to parse .agent/skills/{tool.name}.md: {e}")

    tool_names = {tool.name for tool in manifest.tools}
    if skills_dir.exists():
        for md_file in skills_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue
            skill_name = md_file.stem
            if skill_name not in tool_names:
                warnings.append(f"ORPHAN_CONTRACT: .agent/skills/{md_file.name} has no matching runtime tool")

    return warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="LAS tool manifest and PAP contract manager")
    parser.add_argument(
        "command",
        choices=["generate", "sync", "validate"],
        help="generate a manifest, sync PAP contracts, or validate contract parity",
    )
    parser.add_argument("--output", type=str, help="Output path for tool_manifest.json")
    args = parser.parse_args()

    if AgentEngine is not None:
        engine = AgentEngine(workspace_path=workspace)
        manifest = ToolManifest.from_engine(engine)
    else:
        print(
            "Runtime dependencies are incomplete; using static AST manifest fallback. "
            f"Missing dependency: {ENGINE_IMPORT_ERROR.name if ENGINE_IMPORT_ERROR else 'unknown'}"
        )
        manifest = ToolManifest.from_workspace_static(workspace)
    project_root = Path(workspace).parent

    if args.command == "generate":
        out = manifest.save(args.output)
        print(f"tool_manifest.json written to {out}")
        print(f"{manifest.tool_count} tool(s) registered")

    elif args.command == "sync":
        out = manifest.save(args.output)
        print(f"tool_manifest.json written to {out}")

        written = sync_pap_contracts(manifest, project_root)
        if written:
            print(f"Created {len(written)} new PAP contract(s):")
            for path in written:
                print(f"  + {path}")
        else:
            print("All PAP contracts already exist")

        sync_skills_md(manifest, project_root)
        print(".agent/skills.md updated")

        sync_agent_md_tools(manifest, project_root)
        print(".agent/agent.md tools list synced")

    elif args.command == "validate":
        warnings = validate(manifest, project_root)
        if warnings:
            print(f"{len(warnings)} issue(s) found:")
            for warning in warnings:
                print(f"  {warning}")
            raise SystemExit(1)
        print(f"All {manifest.tool_count} tool(s) have matching PAP contracts")

    print(f"\nManifest ({manifest.manifest_version}):")
    for tool in manifest.tools:
        contract_status = "contract" if tool.pap_contract else "missing-contract"
        print(f"  [{contract_status}] {tool.name}: {tool.description[:60]}")


if __name__ == "__main__":
    main()
