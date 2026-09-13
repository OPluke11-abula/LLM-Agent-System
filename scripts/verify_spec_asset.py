#!/usr/bin/env python3
"""Automated Quality & Compliance Auditor for Engineering Specifications.

Checks generated prompts, specifications, and code against the 4-part architecture:
1. Zero Placeholders (No TODO / dummy mock cop-outs)
2. Hard Token & Hex Palette Locks
3. State Machine & Timeline Coverage
4. Critic-and-Correction Verification Rules
"""

import argparse
import re
import sys
from pathlib import Path

HEX_COLOR_REGEX = re.compile(r"#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}")
TODO_REGEX = re.compile(r"(?://|#|/\*|<!--)\s*(?:TODO|FIXME|TBD|PLACEHOLDER)\b|\b(?:TODO|FIXME|TBD):\s*|pass\s*#|mock_implementation", re.IGNORECASE)


def audit_spec_text(content: str, domain: str) -> tuple[bool, list[str]]:
    """Audit specification text against structural invariants."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Zero Placeholders Invariant
    todo_matches = TODO_REGEX.findall(content)
    if todo_matches:
        errors.append(f"Anti-Corruption Failure: Found placeholder markers: {set(todo_matches)}")

    # 2. Four-Part Structural Coverage
    required_sections = [
        ("Context & Subject / Role", [r"context", r"subject", r"role", r"情境", r"主體", r"角色"]),
        ("Hard Constraints & Tokens", [r"constraint", r"tokens", r"幾何", r"限制", r"網格", r"調色盤"]),
        ("Behavior, Timeline & State", [r"timeline", r"beat", r"state", r"分鏡", r"狀態", r"時間軸", r"motion"]),
        ("Acceptance & Critic Loop", [r"acceptance", r"critic", r"驗收", r"自檢", r"fail condition"]),
    ]

    for sec_name, keywords in required_sections:
        pattern = "|".join(keywords)
        if not re.search(pattern, content, re.IGNORECASE):
            errors.append(f"Missing Structural Section: '{sec_name}' could not be identified.")

    # 3. Domain-specific checks
    domain_clean = domain.lower().strip()
    if domain_clean == "3d":
        # 3D should reject 2D billboard cop-outs and require multi-camera setup
        if not re.search(r"camera|相機|幾何|geometry", content, re.IGNORECASE):
            errors.append("3D Domain Violation: Missing multi-camera or geometry explicit specification.")
    elif domain_clean == "ui":
        # UI should require state handling and responsive dimensions
        if not re.search(r"state|loading|empty|error|狀態", content, re.IGNORECASE):
            errors.append("UI Domain Violation: Missing required 5-state machine definitions.")
    elif domain_clean == "2d":
        # 2D should require grid size / frame timeline / palette
        if not re.search(r"frame|grid|pixel|sprite|幀|網格", content, re.IGNORECASE):
            errors.append("2D Domain Violation: Missing frame sequencing or grid dimension constraints.")

    # 4. Color discipline check
    hex_colors = HEX_COLOR_REGEX.findall(content)
    if not hex_colors and "hex" not in content.lower() and "調色" not in content:
        warnings.append("Warning: No strict Hex color codes or palette constraint detected.")

    is_success = len(errors) == 0
    return is_success, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audits engineering specifications and generative outputs.")
    parser.add_argument("--domain", choices=["3d", "ui", "2d"], default="ui", help="Creative domain")
    parser.add_argument("--file", type=str, help="Path to specification file to audit")
    parser.add_argument("--content", type=str, help="Direct specification content string")
    parser.add_argument("--verbose", action="store_true", help="Print verbose details")

    args = parser.parse_args()

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"[FAIL] File not found: {args.file}", file=sys.stderr)
            return 1
        raw_content = file_path.read_text(encoding="utf-8")
    elif args.content:
        raw_content = args.content
    else:
        print("[FAIL] Either --file or --content must be specified.", file=sys.stderr)
        return 1

    success, errors = audit_spec_text(raw_content, args.domain)

    if success:
        print(f"[PASS] Engineering Specification Audit PASSED for domain: '{args.domain}' (0 Invariant Violations).")
        return 0
    else:
        print(f"[FAIL] Engineering Specification Audit FAILED with {len(errors)} violation(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
