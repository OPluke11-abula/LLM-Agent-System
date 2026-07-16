from pathlib import Path

import pytest

from agent_workspace.core.security import validate_bind_security


SECURE_AUTH = {"jwt_secret": "s" * 40}


@pytest.mark.parametrize("host", ["127.0.0.1", " localhost ", "::1"])
def test_loopback_bindings_are_allowed_without_auth(host):
    state = validate_bind_security(host, {})
    assert state.host in {"127.0.0.1", "localhost", "::1"}
    assert state.external is False


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.20", "api.example.test"])
def test_external_bindings_require_secure_auth(host):
    with pytest.raises(ValueError, match="secure authentication"):
        validate_bind_security(host, {})


@pytest.mark.parametrize("secret", [None, "", "   ", "default", "change-me", "test-only-secret"])
def test_external_binding_rejects_blank_or_placeholder_secrets(secret):
    with pytest.raises(ValueError, match="secure authentication"):
        validate_bind_security("0.0.0.0", {"jwt_secret": secret})


def test_external_binding_accepts_secure_authentication():
    state = validate_bind_security("0.0.0.0", SECURE_AUTH)
    assert state.external is True
    assert state.host == "0.0.0.0"


def test_hostname_resolution_ambiguity_requires_auth(monkeypatch):
    monkeypatch.setattr(
        "agent_workspace.core.security.socket.getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 0)), (None, None, None, None, ("10.0.0.4", 0))],
    )
    with pytest.raises(ValueError, match="secure authentication"):
        validate_bind_security("mixed.example.test", {})


def test_server_launcher_defaults_to_loopback(monkeypatch):
    import agent_workspace.server as server

    calls = {}
    monkeypatch.setattr(server.uvicorn, "run", lambda *args, **kwargs: calls.update(kwargs))
    server.run_server()
    assert calls["host"] == "127.0.0.1"


def test_server_launcher_validates_external_bind_before_launch(monkeypatch):
    import agent_workspace.server as server

    monkeypatch.setattr(server.uvicorn, "run", lambda *args, **kwargs: pytest.fail("server launched"))
    with pytest.raises(ValueError, match="secure authentication"):
        server.run_server(host="0.0.0.0", auth_config={})


def test_server_cli_launcher_allows_external_bind_with_secure_auth(monkeypatch):
    import agent_workspace.server as server

    monkeypatch.setenv("LAS_JWT_SECRET", "s" * 40)
    calls = {}
    monkeypatch.setattr(server.uvicorn, "run", lambda *args, **kwargs: calls.update(kwargs))
    server.main(["--host", "0.0.0.0", "--port", "8001"])
    assert calls["host"] == "0.0.0.0"
    assert calls["port"] == 8001


def test_docker_default_does_not_bind_publicly():
    dockerfile = Path(__file__).parents[2] / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    assert "0.0.0.0" not in content
    assert "127.0.0.1" in content

    compose = (dockerfile.parents[0] / "docker-compose.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8000:8000"' in compose
    assert "LAS_BIND_HOST=${LAS_BIND_HOST:-127.0.0.1}" in compose
