from __future__ import annotations

import argparse
import os

import uvicorn

from agent_workspace.core.security import validate_bind_security


def run_server(
    host: str | None = None,
    port: int = 8000,
    auth_config: dict[str, object] | None = None,
    **uvicorn_kwargs: object,
) -> None:
    requested_host = host if host is not None else os.environ.get("LAS_BIND_HOST", "127.0.0.1")
    configured_auth = auth_config if auth_config is not None else {
        "jwt_secret": os.environ.get("LAS_JWT_SECRET"),
    }
    state = validate_bind_security(requested_host, configured_auth)
    uvicorn.run(
        "agent_workspace.api:app",
        host=state.host,
        port=port,
        **uvicorn_kwargs,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the LAS API server safely.")
    parser.add_argument("--host", default=os.environ.get("LAS_BIND_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
