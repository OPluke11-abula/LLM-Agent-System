"""Validate the LAS PAP workspace contract using JSON Schema and path verification."""

from __future__ import annotations

import json
import re
from pathlib import Path
import yaml
import jsonschema

# Reference protocol and runtime version defaults
PROTOCOL_VERSION = "1.0.0"
RUNTIME_VERSION = "0.5.0"


def parse_version(v_str: str) -> tuple[int, int, int]:
    """Parse a semantic version string (e.g. 'v1.2.3', '0.1.0-alpha') into a numeric tuple."""
    if v_str.startswith('v'):
        v_str = v_str[1:]
    parts = []
    for p in v_str.split('.'):
        match = re.match(r'^(\d+)', p)
        if match:
            parts.append(int(match.group(1)))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


def extract_frontmatter(manifest_path: Path) -> str:
    raw = manifest_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{manifest_path} does not contain YAML front matter")
    return parts[1]


def validate(root: Path) -> None:
    manifest_path = root / ".agent" / "agent.md"
    if not manifest_path.is_file():
        raise FileNotFoundError(".agent/agent.md is missing")

    frontmatter_str = extract_frontmatter(manifest_path)
    try:
        config = yaml.safe_load(frontmatter_str) or {}
    except Exception as e:
        raise ValueError(f"Failed to parse agent.md front-matter YAML: {e}")

    # 1. Validate against JSON schema
    schema_path = root / "spec" / "agent-schema.json"
    if not schema_path.is_file():
        fallback_path = Path(__file__).resolve().parent.parent / "spec" / "agent-schema.json"
        if fallback_path.is_file():
            schema_path = fallback_path
        else:
            raise FileNotFoundError(f"Schema not found at {schema_path}")

    try:
        with schema_path.open(encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.validate(instance=config, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.message}") from e

    # 2. Semantic version checks
    proto_ver = config.get("protocol_version", "1.0.0")
    min_run_ver = config.get("min_runtime_version", "0.1.0")

    try:
        curr_run = parse_version(RUNTIME_VERSION)
        req_run = parse_version(min_run_ver)
        if curr_run < req_run:
            raise ValueError(
                f"Incompatible runtime version: required min {min_run_ver}, current {RUNTIME_VERSION}"
            )
    except ValueError as e:
        raise e
    except Exception:
        pass

    try:
        req_proto = parse_version(proto_ver)
        supp_proto = parse_version(PROTOCOL_VERSION)
        if req_proto[0] != supp_proto[0]:
            raise ValueError(
                f"Incompatible protocol version major mismatch: manifest uses {proto_ver}, supported is {PROTOCOL_VERSION}"
            )
    except ValueError as e:
        raise e
    except Exception:
        pass

    # 3. Dynamic path resolution & checks
    protocol = config.get("protocol", {})
    if isinstance(protocol, dict):
        # Resolve roots relative to project root (which is parent of .agent directory)
        project_root = root

        # Check protocol.root
        if "root" in protocol:
            root_path = project_root / protocol["root"]
            if not root_path.is_dir():
                raise FileNotFoundError(f"protocol.root directory does not exist: {root_path}")

        # Check protocol.manifest
        if "manifest" in protocol:
            manifest_p = project_root / protocol["manifest"]
            if not manifest_p.is_file():
                raise FileNotFoundError(f"protocol.manifest file does not exist: {manifest_p}")

        # Check protocol.entrypoints
        entrypoints = protocol.get("entrypoints", {})
        if isinstance(entrypoints, dict):
            for k, val in entrypoints.items():
                if isinstance(val, str):
                    p = project_root / val
                    if not p.is_file():
                        raise FileNotFoundError(f"protocol.entrypoints.{k} file does not exist: {p}")

        # Check protocol.directories
        directories = protocol.get("directories", {})
        if isinstance(directories, dict):
            for k, val in directories.items():
                if isinstance(val, str):
                    d = project_root / val
                    if not d.is_dir():
                        raise FileNotFoundError(f"protocol.directories.{k} directory does not exist: {d}")

    # 4. Check registered local skills
    tools = config.get("tools", [])
    if not tools:
        raise ValueError("Manifest must declare at least one tool")

    # Resolve skills directory
    skills_dir = root / ".agent" / "skills"
    if isinstance(protocol, dict):
        directories = protocol.get("directories", {})
        if isinstance(directories, dict) and "skills" in directories:
            skills_dir = project_root / directories["skills"]

    missing_skill_docs = []
    for tool in tools:
        skill_doc = skills_dir / f"{tool}.md"
        if not skill_doc.is_file():
            missing_skill_docs.append(str(skill_doc.relative_to(root).as_posix()))

    if missing_skill_docs:
        raise FileNotFoundError(f"Missing skill contracts: {missing_skill_docs}")

    print(f"PAP workspace valid: {manifest_path}")
    print(f"Tools: {', '.join(tools)}")


if __name__ == "__main__":
    import sys
    validate(Path(__file__).resolve().parents[1])
