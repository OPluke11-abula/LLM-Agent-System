#!/usr/bin/env python3
"""LAS Developer Beta: Local Daemon & Control Plane Launcher (Phase 84 / P5).

Starts the FastAPI backend gateway and WebSocket telemetry hub, validates runtime
environment, and optionally launches the frontend developer cockpit.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import webbrowser
from pathlib import Path

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add repository root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BANNER = r"""
  _        _     ____
 | |      / \   / ___|
 | |     / _ \  \___ \
 | |___ / ___ \  ___) |
 |_____/_/   \_\|____/  Developer Control Plane (v0.5.0)
 Universal Coding Agent Development Protocol v3.8.0
"""


def verify_runtime_dependencies() -> bool:
    """Check that mandatory packages are installed."""
    missing: list[str] = []
    for pkg in ("fastapi", "uvicorn", "pydantic", "httpx"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"❌ Missing required dependencies: {', '.join(missing)}", file=sys.stderr)
        print("   Run: pip install -e .", file=sys.stderr)
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the LAS developer control plane daemon.")
    parser.add_argument("--host", default=os.environ.get("LAS_BIND_HOST", "127.0.0.1"), help="Host to bind")
    parser.add_argument("--port", type=int, default=int(os.environ.get("LAS_BIND_PORT", "8000")), help="API port")
    parser.add_argument("--open-browser", action="store_true", default=True, help="Automatically open browser cockpit")
    parser.add_argument("--no-browser", dest="open_browser", action="store_false", help="Do not open browser")
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload for local dev")
    args = parser.parse_args()

    print(BANNER)
    print("=" * 65)
    print(f" 🌐 Target Root        : {REPO_ROOT}")
    print(f" 🔌 REST & WS Gateway  : http://{args.host}:{args.port}")
    print(f" 📖 Swagger OpenAPI    : http://{args.host}:{args.port}/docs")
    print(f" 🖥️ Developer Cockpit  : http://localhost:5173/pipeline")
    print("=" * 65)

    if not verify_runtime_dependencies():
        sys.exit(1)

    if args.open_browser:
        target_url = f"http://{args.host}:{args.port}/docs"
        viewer_dist = REPO_ROOT / "viewer" / "dist" / "index.html"
        if viewer_dist.exists():
            target_url = "http://localhost:5173/pipeline"
        print(f"\n🚀 Opening browser to: {target_url}")
        try:
            webbrowser.open(target_url)
        except Exception:
            pass

    import uvicorn
    from agent_workspace.core.security import validate_bind_security

    auth_config = {"jwt_secret": os.environ.get("LAS_JWT_SECRET")}
    state = validate_bind_security(args.host, auth_config)

    print(f"\n✨ LAS Daemon listening on http://{state.host}:{args.port} (Press Ctrl+C to stop)...")
    uvicorn.run(
        "agent_workspace.api:app",
        host=state.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
