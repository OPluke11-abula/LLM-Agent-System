"""Phase 108 Test Suite: Docker Multi-Arch Buildx & GHCR Registry Pipeline Verification.

Validates:
1. Dockerfile invariants (Multi-stage build, rootless lasuser, health check, expose 8000).
2. Production configuration template (.env.production.example completeness and safety).
3. GitHub Actions GHCR workflow (.github/workflows/docker-publish.yml structure, permissions, and Buildx).
4. Docker Compose orchestration integrity (docker-compose.yml and volume bindings).
"""

from __future__ import annotations

import re
from pathlib import Path
import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_dockerfile_security_and_runtime_invariants():
    """Validates that Dockerfile adheres to rootless security and multi-stage build standards."""
    dockerfile_path = PROJECT_ROOT / "Dockerfile"
    assert dockerfile_path.is_file(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")

    # 1. Multi-stage build
    assert "FROM node:" in content, "Must have Node stage for frontend build"
    assert "AS frontend-builder" in content, "Frontend stage must be named frontend-builder"
    assert "FROM python:" in content, "Must have Python final stage"

    # 2. Unprivileged user & group
    assert "groupadd -g 1001 lasgroup" in content, "Must create lasgroup with GID 1001"
    assert "useradd -u 1001 -g lasgroup" in content, "Must create lasuser with UID 1001"
    assert "USER lasuser" in content, "Container must drop privileges to lasuser"

    # 3. Port and Health Check
    assert "EXPOSE 8000" in content, "Must expose standard port 8000"
    assert "HEALTHCHECK" in content, "Must configure container healthcheck"
    assert "/v1/health" in content, "Healthcheck must target /v1/health endpoint"

    # 4. Invariants for Python bytecode & buffering
    assert "ENV PYTHONDONTWRITEBYTECODE=1" in content
    assert "ENV PYTHONUNBUFFERED=1" in content


def test_production_env_template_completeness():
    """Validates that .env.production.example provides safe, complete configuration keys."""
    env_example_path = PROJECT_ROOT / ".env.production.example"
    assert env_example_path.is_file(), ".env.production.example must exist"

    content = env_example_path.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
    keys = {line.split("=")[0].strip() for line in lines}

    required_keys = {
        "LAS_BIND_HOST",
        "PORT",
        "LAS_JWT_SECRET",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "LAS_ENABLE_REDIS_SWARM",
        "LAS_DATA_DIR",
        "LAS_MEMORY_DIR",
        "LAS_WORKSPACE_DIR",
    }
    missing = required_keys - keys
    assert not missing, f"Missing required production env keys: {missing}"

    # Ensure no actual sensitive keys are committed in template
    for line in lines:
        if "=" in line:
            k, v = line.split("=", 1)
            if "API_KEY" in k:
                assert v == "", f"Template must not contain real secret for {k}"


def test_github_actions_docker_publish_workflow_syntax():
    """Validates the syntax and security configuration of the GHCR publish workflow."""
    workflow_path = PROJECT_ROOT / ".github" / "workflows" / "docker-publish.yml"
    assert workflow_path.is_file(), "docker-publish.yml must exist"

    content = workflow_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    assert "name" in parsed
    # In YAML 1.1, unquoted 'on' is parsed as boolean True
    on_triggers = parsed.get("on") or parsed.get(True)
    assert on_triggers is not None, "Workflow must define triggers"
    assert "push" in on_triggers
    assert "pull_request" in on_triggers


    # Check permissions
    perms = parsed.get("permissions", {})
    assert perms.get("packages") == "write", "Workflow requires packages: write for GHCR"
    assert perms.get("contents") == "read", "Workflow requires contents: read"

    # Check jobs
    jobs = parsed.get("jobs", {})
    assert "build-and-push" in jobs
    steps = jobs["build-and-push"].get("steps", [])

    step_uses = [s.get("uses", "") for s in steps]
    assert any("docker/setup-qemu-action" in u for u in step_uses), "Must configure QEMU"
    assert any("docker/setup-buildx-action" in u for u in step_uses), "Must configure Buildx"
    assert any("docker/login-action" in u for u in step_uses), "Must configure Docker login"
    assert any("docker/build-push-action" in u for u in step_uses), "Must configure build-push-action"


def test_docker_compose_production_compatibility():
    """Validates docker-compose.yml configuration and volume isolation."""
    compose_path = PROJECT_ROOT / "docker-compose.yml"
    assert compose_path.is_file(), "docker-compose.yml must exist"

    content = compose_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    services = parsed.get("services", {})
    assert "backend" in services, "Must define backend service"
    assert "frontend" in services, "Must define frontend service"

    backend = services["backend"]
    assert backend.get("build", {}).get("dockerfile") == "Dockerfile"

    volumes = parsed.get("volumes", {})
    assert "agent_data" in volumes
    assert "memory_data" in volumes
    assert "workspace_data" in volumes
