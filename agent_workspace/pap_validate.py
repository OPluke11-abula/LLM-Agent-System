"""Validate the LAS PAP workspace contract without external dependencies."""

from __future__ import annotations

from pathlib import Path


REQUIRED_MANIFEST_KEYS = {
    "protocol_version",
    "min_runtime_version",
    "name",
    "version",
    "purpose",
    "language",
    "authorization_level",
    "use_case_tags",
    "tools",
}

REQUIRED_ENTRYPOINTS = (
    ".agent/README.md",
    ".agent/skills.md",
    ".agent/prompts.md",
    ".agent/memory.md",
    ".agent/workflows.md",
)


def extract_frontmatter(manifest_path: Path) -> str:
    raw = manifest_path.read_text(encoding="utf-8")
    parts = raw.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{manifest_path} does not contain YAML front matter")
    return parts[1]


def frontmatter_keys(frontmatter: str) -> set[str]:
    keys: set[str] = set()
    for line in frontmatter.splitlines():
        if not line or line.startswith(" ") or line.startswith("-"):
            continue
        if ":" in line:
            keys.add(line.split(":", 1)[0].strip())
    return keys


def frontmatter_list(frontmatter: str, key: str) -> list[str]:
    lines = frontmatter.splitlines()
    items: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        if stripped == f"{key}:":
            collecting = True
            continue
        if collecting:
            if not line.startswith(" ") and stripped and not stripped.startswith("-"):
                break
            if stripped.startswith("- "):
                items.append(stripped[2:].strip().strip("\"'"))
    return items


def validate(root: Path) -> None:
    manifest_path = root / ".agent" / "agent.md"
    if not manifest_path.is_file():
        raise FileNotFoundError(".agent/agent.md is missing")

    frontmatter = extract_frontmatter(manifest_path)
    missing_keys = sorted(REQUIRED_MANIFEST_KEYS - frontmatter_keys(frontmatter))
    if missing_keys:
        raise ValueError(f"Missing manifest keys: {missing_keys}")

    tools = frontmatter_list(frontmatter, "tools")
    if not tools:
        raise ValueError("Manifest must declare at least one tool")

    missing_entrypoints = [path for path in REQUIRED_ENTRYPOINTS if not (root / path).is_file()]
    if missing_entrypoints:
        raise FileNotFoundError(f"Missing PAP entry documents: {missing_entrypoints}")

    missing_skill_docs = [
        f".agent/skills/{tool}.md"
        for tool in tools
        if not (root / ".agent" / "skills" / f"{tool}.md").is_file()
    ]
    if missing_skill_docs:
        raise FileNotFoundError(f"Missing skill contracts: {missing_skill_docs}")

    print(f"PAP workspace valid: {manifest_path}")
    print(f"Tools: {', '.join(tools)}")


if __name__ == "__main__":
    validate(Path(__file__).resolve().parents[1])
