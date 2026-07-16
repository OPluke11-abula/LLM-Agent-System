from __future__ import annotations

import ipaddress
import hashlib
import os
import re
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import urlsplit


_PROVIDER_HOSTS = {
    "openai": "api.openai.com",
    "anthropic": "api.anthropic.com",
    "google-genai": "generativelanguage.googleapis.com",
}
_OLLAMA_HOSTS = {"localhost", "127.0.0.1", "::1"}
_SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def get_secret_bytes(env_name: str) -> bytes:
    """Load a secret or fail closed; only explicit test mode permits a marker."""
    configured = os.environ.get(env_name)
    if configured:
        return configured.encode("utf-8")
    if os.environ.get("LAS_TEST_MODE", "").lower() in {"1", "true", "yes"}:
        return f"test-only:{env_name}".encode("utf-8")
    raise RuntimeError(f"Required secret {env_name} is not configured.")


@dataclass(frozen=True)
class BindSecurityState:
    host: str
    external: bool
    auth_configured: bool


class StartupConfigurationError(ValueError):
    pass


_INSECURE_SECRET_MARKERS = (
    "change-me",
    "changeme",
    "default",
    "development",
    "insecure",
    "placeholder",
    "test-only",
    "your-secret",
)


def _secure_auth_configured(auth_config: Mapping[str, object] | None) -> bool:
    if not isinstance(auth_config, Mapping):
        return False
    secret = auth_config.get("jwt_secret") or auth_config.get("LAS_JWT_SECRET")
    if isinstance(secret, str):
        normalized = secret.strip().lower()
        if len(secret.strip()) >= 32 and not any(marker in normalized for marker in _INSECURE_SECRET_MARKERS):
            return True
    api_keys = auth_config.get("api_keys")
    if isinstance(api_keys, Mapping):
        return any(
            isinstance(value, str)
            and len(value.strip()) >= 32
            and not any(marker in value.strip().lower() for marker in _INSECURE_SECRET_MARKERS)
            for value in api_keys.values()
        )
    return False


def _resolved_host_addresses(host: str) -> set[str]:
    try:
        results = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (OSError, socket.gaierror):
        return set()
    addresses: set[str] = set()
    for result in results:
        sockaddr = result[4]
        if isinstance(sockaddr, tuple) and sockaddr:
            addresses.add(str(sockaddr[0]).split("%", 1)[0])
    return addresses


def validate_bind_security(
    host: str | None,
    auth_config: Mapping[str, object] | None = None,
) -> BindSecurityState:
    raw_host = "127.0.0.1" if host is None or not str(host).strip() else str(host).strip()
    if raw_host.startswith("[") and raw_host.endswith("]"):
        raw_host = raw_host[1:-1]
    if any(char.isspace() or ord(char) < 32 for char in raw_host):
        raise StartupConfigurationError("Bind host is malformed.")

    normalized_host = raw_host.lower().rstrip(".")
    external = True
    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        if normalized_host == "localhost":
            external = False
        else:
            resolved = _resolved_host_addresses(normalized_host)
            external = not resolved or any(not ipaddress.ip_address(item).is_loopback for item in resolved)
    else:
        normalized_host = address.compressed
        external = not address.is_loopback

    auth_configured = _secure_auth_configured(auth_config)
    if external and not auth_configured:
        raise StartupConfigurationError(
            "External bind host requires secure authentication."
        )
    return BindSecurityState(
        host=normalized_host,
        external=external,
        auth_configured=auth_configured,
    )


def validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or _SESSION_ID_PATTERN.fullmatch(session_id) is None:
        raise ValueError("Invalid session ID.")
    return session_id


def build_child_session_id(parent_session: str, worker_name: str) -> str:
    parent = validate_session_id(parent_session)
    worker = validate_session_id(worker_name)
    derived = f"{parent}_{worker}"
    if len(derived) <= 128:
        return validate_session_id(derived)

    digest = hashlib.sha256(derived.encode("utf-8")).hexdigest()[:16]
    readable_prefix = derived[: 128 - len(digest) - 1]
    return validate_session_id(f"{readable_prefix}_{digest}")


def safe_workspace_path(workspace_root: str | Path, relative_path: str | Path) -> Path:
    raw_path = os.fspath(relative_path)
    if isinstance(raw_path, bytes):
        raw_path = os.fsdecode(raw_path)
    if not isinstance(raw_path, str) or not raw_path or "%" in raw_path:
        raise ValueError("Workspace path must be an unencoded relative path.")
    if any(char.isspace() or ord(char) < 32 for char in raw_path):
        raise ValueError("Workspace path contains control characters.")

    windows_path = PureWindowsPath(raw_path)
    if PurePosixPath(raw_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise ValueError("Workspace path must remain relative to the workspace.")

    normalized = raw_path.replace("\\", "/")
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise ValueError("Workspace path contains traversal components.")

    root = Path(workspace_root).resolve()
    candidate = (root / Path(normalized)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("Workspace path escapes the workspace root.") from error
    return candidate


def validate_provider_base_url(provider_name: str, base_url: str) -> str:
    if not isinstance(base_url, str):
        raise ValueError("Provider base URL must be a string.")
    value = base_url.strip()
    if not value or any(char.isspace() or ord(char) < 32 for char in value):
        raise ValueError("Provider base URL is malformed.")

    provider = provider_name.strip().lower()
    if provider == "gemini":
        provider = "google-genai"
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("Provider base URL is malformed.") from error

    if parsed.scheme not in {"http", "https"} or not hostname:
        raise ValueError("Provider base URL must use an HTTP(S) URL with a host.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Provider base URL must not contain credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("Provider base URL must not contain a query or fragment.")

    hostname = hostname.lower().rstrip(".")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None

    if provider == "ollama":
        if parsed.scheme != "http" or hostname not in _OLLAMA_HOSTS or port != 11434:
            raise ValueError("Ollama base URL must target localhost on HTTP port 11434.")
        return value

    expected_host = _PROVIDER_HOSTS.get(provider)
    if address is not None or expected_host is None:
        raise ValueError("Provider base URL host is not allowed.")
    if parsed.scheme != "https" or hostname != expected_host or port not in {None, 443}:
        raise ValueError("Provider base URL host or scheme is not allowed.")
    return value
