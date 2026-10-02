import os
import sys
import hashlib
import ast
import logging
import tempfile
import shutil
from typing import Any, Dict

logger = logging.getLogger(__name__)

SNAPSHOT_IGNORED_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".uv-cache",
    ".path-backups",
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "output",
    "scratch",
    "coverage",
    "cover",
    "target",
}


def _is_snapshot_ignored_dir(name: str) -> bool:
    return name.startswith(".") or name in SNAPSHOT_IGNORED_DIRS


def _copy_snapshot_entry(src_path: str, dst_path: str) -> None:
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    if os.path.islink(src_path):
        os.symlink(os.readlink(src_path), dst_path, target_is_directory=os.path.isdir(src_path))
        return
    shutil.copy2(src_path, dst_path, follow_symlinks=False)


class FileSnapshotTransaction:
    """Manages workspace snapshots and automatically rolls back modified files on failure."""
    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.temp_dir = None

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        for root, dirs, files in os.walk(self.workspace_path):
            kept_dirs = []
            for directory in dirs:
                if _is_snapshot_ignored_dir(directory):
                    continue
                src_dir = os.path.join(root, directory)
                if os.path.islink(src_dir):
                    rel_dir_path = os.path.relpath(src_dir, self.workspace_path)
                    dst_dir = os.path.join(self.temp_dir, rel_dir_path)
                    try:
                        _copy_snapshot_entry(src_dir, dst_dir)
                    except Exception as e:
                        logger.warning("[FileSnapshotTransaction] Failed to snapshot directory symlink %s: %s", src_dir, e)
                    continue
                kept_dirs.append(directory)
            dirs[:] = kept_dirs
            for file in files:
                src_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(src_path, self.workspace_path)
                dst_path = os.path.join(self.temp_dir, rel_file_path)
                try:
                    _copy_snapshot_entry(src_path, dst_path)
                except Exception as e:
                    logger.warning("[FileSnapshotTransaction] Failed to snapshot file %s: %s", src_path, e)
        return self

    def rollback(self):
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return
        logger.info("[FileSnapshotTransaction] Initiating rollback for workspace: %s", self.workspace_path)

        # 1. Delete all non-ignored files in the workspace
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if not _is_snapshot_ignored_dir(d)]
            for directory in list(dirs):
                dir_path = os.path.join(root, directory)
                if not os.path.islink(dir_path):
                    continue
                try:
                    os.rmdir(dir_path)
                except Exception as e:
                    logger.warning("[FileSnapshotTransaction] Failed to delete directory symlink during rollback: %s: %s", dir_path, e)
                dirs.remove(directory)
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning("[FileSnapshotTransaction] Failed to delete file during rollback: %s: %s", file_path, e)

        for root, dirs, files in os.walk(self.workspace_path, topdown=False):
            rel_root = os.path.relpath(root, self.workspace_path)
            parts = [p for p in rel_root.split(os.sep) if p and p != "."]
            if not parts or any(_is_snapshot_ignored_dir(p) for p in parts):
                continue
            try:
                os.rmdir(root)
            except OSError:
                pass
            except Exception as e:
                logger.warning("[FileSnapshotTransaction] Failed to remove directory during rollback: %s: %s", root, e)

        # 2. Restore files from the snapshot
        for root, dirs, files in os.walk(self.temp_dir):
            for directory in list(dirs):
                src_dir = os.path.join(root, directory)
                if not os.path.islink(src_dir):
                    continue
                rel_dir_path = os.path.relpath(src_dir, self.temp_dir)
                dst_dir = os.path.join(self.workspace_path, rel_dir_path)
                try:
                    _copy_snapshot_entry(src_dir, dst_dir)
                except Exception as e:
                    logger.error("[FileSnapshotTransaction] Failed to restore directory symlink during rollback: %s: %s", dst_dir, e)
                dirs.remove(directory)
            for file in files:
                src_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(src_path, self.temp_dir)
                dst_path = os.path.join(self.workspace_path, rel_file_path)
                try:
                    _copy_snapshot_entry(src_path, dst_path)
                except Exception as e:
                    logger.error("[FileSnapshotTransaction] Failed to restore file during rollback: %s: %s", dst_path, e)

    def cleanup(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning("[FileSnapshotTransaction] Failed to cleanup temp dir: %s", e)
            self.temp_dir = None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.cleanup()
        return False  # Propagate exception


def make_safe_open(workspace_path: str):
    """Generates a restricted open() builtin that prevents path traversal outside the designated workspace."""
    abs_workspace = os.path.realpath(os.path.abspath(workspace_path))

    def safe_open(file, mode='r', *args, **kwargs):
        if not isinstance(file, (str, bytes, os.PathLike)):
            raise PermissionError(f"Security violation: File descriptor access is not allowed: '{file}'")

        file_path = os.fspath(file)
        if isinstance(file_path, bytes):
            decoded_file = file_path.decode("utf-8", errors="replace")
        else:
            decoded_file = file_path

        # Resolve to absolute path
        if os.path.isabs(decoded_file):
            resolved_path = os.path.realpath(os.path.abspath(decoded_file))
        else:
            resolved_path = os.path.realpath(os.path.abspath(os.path.join(abs_workspace, decoded_file)))

        try:
            rel = os.path.relpath(resolved_path, abs_workspace)
            if rel == os.pardir or rel.startswith(os.pardir + os.sep) or os.path.isabs(rel):
                raise PermissionError(f"Security violation: Directory traversal attempt outside workspace boundaries: '{file}'")
        except ValueError:
            raise PermissionError(f"Security violation: Directory traversal attempt outside workspace boundaries: '{file}'")

        return open(resolved_path, mode, *args, **kwargs)

    return safe_open


def validate_generated_skill(code_content: str) -> tuple[ast.AST, str]:
    try:
        tree = ast.parse(code_content)
    except SyntaxError as exc:
        raise ValueError(f"Syntax error in generated code: {exc}") from exc

    allowed_imports = {"pydantic", "typing", "typing_extensions"}
    blocked_calls = {"eval", "exec", "compile", "system", "popen", "run", "__import__"}
    model_name = ""
    has_function = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module = node.module if isinstance(node, ast.ImportFrom) else None
            names = [alias.name for alias in node.names]
            roots = [module] if module else names
            if any(root and root.split(".")[0] not in allowed_imports for root in roots):
                raise PermissionError("Security violation: generated skill imports are restricted")
            if any(alias.startswith("_") for alias in names):
                raise PermissionError("Security violation: private generated-skill import")
        elif isinstance(node, ast.Call):
            call_name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            if call_name in blocked_calls:
                raise PermissionError(f"Security violation: unsafe execution call '{call_name}' detected")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise PermissionError("Security violation: private generated-skill attribute")
        elif isinstance(node, ast.Name) and node.id.startswith("__"):
            raise PermissionError("Security violation: private generated-skill name")

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if any(isinstance(base, ast.Name) and base.id == "BaseModel" for base in node.bases):
                model_name = node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            if node.args.args and node.args.args[0].annotation:
                annotation = node.args.args[0].annotation
                if isinstance(annotation, ast.Name) and annotation.id == model_name:
                    has_function = True
    if not model_name:
        raise ValueError("Generated skill must define a Pydantic BaseModel argument class")
    if not has_function:
        raise ValueError("Generated skill must define a public function whose first parameter is annotated with the Pydantic BaseModel")
    return tree, model_name


def validate_skill_name(name: str) -> None:
    if not name.isidentifier() or len(name) > 64:
        raise ValueError("Generated skill name must be a simple Python identifier")


class SandboxGuard:
    """Safely isolates and executes dynamically generated dynamic tasks, workflow custom scripts, and code blocks under a Zero-Trust policy."""

    BLOCKED_MODULES = {"os", "sys", "subprocess", "shutil", "socket", "urllib", "requests", "ctypes"}
    BLOCKED_BUILTINS = {"eval", "exec", "compile", "open", "input", "globals", "locals", "__import__"}

    total_executions = 0
    blocked_executions = 0
    allowed_executions = 0
    last_execution_status = "none"

    DOCKER_IMAGE = os.environ.get("LAS_SANDBOX_IMAGE", "python:3.11-slim")
    MEMORY_LIMIT = "128m"
    CPU_LIMIT = 500_000_000
    PIDS_LIMIT = 64
    TIMEOUT_SECONDS = 10.0
    MAX_OUTPUT_BYTES = 1_048_576

    @classmethod
    def execute_safe(
        cls,
        workspace_path: str,
        code_content: str,
        globals_dict: Dict[str, Any] = None,
        locals_dict: Dict[str, Any] = None,
        sandbox_type: str = "ast",
        tenant_id: str = "default_tenant"
    ) -> Dict[str, Any]:
        cls.total_executions += 1

        # 1. Consensus Verification
        payload_hash = hashlib.sha256(code_content.encode("utf-8")).hexdigest()
        from agent_workspace.core.discussion_room import ProofOfConsensus

        if not ProofOfConsensus.is_consensus_approved(workspace_path, payload_hash):
            cls.blocked_executions += 1
            cls.last_execution_status = "blocked"
            try:
                from agent_workspace.observability import PROMETHEUS_AVAILABLE, _get_or_create_metric
                if PROMETHEUS_AVAILABLE:
                    from prometheus_client import Counter
                    sandbox_count = _get_or_create_metric(Counter, "las_sandbox_executions_total", "Total sandbox executions", ["tenant_id", "status"])
                    sandbox_count.labels(tenant_id=tenant_id, status=cls.last_execution_status).inc()
            except Exception:
                pass
            try:
                from core.audit_ledger import AuditLedger
                audit = AuditLedger(workspace_path)
                audit.record_event("system_call", {
                    "sandbox_type": sandbox_type,
                    "code_hash": payload_hash,
                    "status": "blocked",
                    "error": "Consensus signature verification failed."
                }, tenant_id=tenant_id)
            except Exception:
                pass
            raise PermissionError("Security violation: Sandbox execution blocked. Consensus signature verification failed.")

        if sandbox_type.lower() != "docker":
            cls.blocked_executions += 1
            cls.last_execution_status = "blocked"
            raise PermissionError(
                "Security violation: in-process sandbox execution is disabled; "
                "use sandbox_type='docker'."
            )

        import subprocess

        docker_client = None
        try:
            import docker
            docker_client = docker.from_env()
            docker_client.ping()
        except Exception as exc:
            docker_client = None
            logger.debug("Docker SDK unavailable: %s", exc)

        if docker_client is None:
            try:
                probe = subprocess.run(
                    ["docker", "info"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=5.0,
                )
            except Exception as exc:
                probe = None
                logger.debug("Docker CLI unavailable: %s", exc)
            if probe is None or probe.returncode != 0:
                cls.blocked_executions += 1
                cls.last_execution_status = "blocked"
                raise RuntimeError(
                    "Docker sandbox unavailable; refusing in-process execution."
                )

        image = os.environ.get("LAS_SANDBOX_IMAGE", cls.DOCKER_IMAGE)
        if not image:
            raise RuntimeError("LAS_SANDBOX_IMAGE must identify a trusted sandbox image")
        command = ["python", "-I", "-B", "-c", code_content]
        container = None
        exit_code = -1
        stdout = ""
        stderr = ""
        try:
            if docker_client is not None:
                container = docker_client.containers.run(
                    image=image,
                    command=command,
                    mem_limit=cls.MEMORY_LIMIT,
                    nano_cpus=cls.CPU_LIMIT,
                    pids_limit=cls.PIDS_LIMIT,
                    network_mode="none",
                    read_only=True,
                    cap_drop=["ALL"],
                    security_opt=["no-new-privileges:true"],
                    tmpfs={"/tmp": "rw,noexec,nosuid,size=16m"},
                    user="65532:65532",
                    detach=True,
                    stdout=True,
                    stderr=True,
                )
                result = container.wait(timeout=cls.TIMEOUT_SECONDS)
                exit_code = int(result.get("StatusCode", 1))
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", "replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", "replace")
            else:
                result = subprocess.run(
                    [
                        "docker", "run", "--rm", "--init",
                        "--memory", cls.MEMORY_LIMIT,
                        "--cpus", "0.5",
                        "--pids-limit", str(cls.PIDS_LIMIT),
                        "--network", "none", "--read-only",
                        "--cap-drop", "ALL",
                        "--security-opt", "no-new-privileges:true",
                        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                        "--user", "65532:65532", image, *command,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                    timeout=cls.TIMEOUT_SECONDS,
                )
                exit_code = result.returncode
                stdout = result.stdout
                stderr = result.stderr
        except Exception as exc:
            cls.blocked_executions += 1
            cls.last_execution_status = "failed"
            raise RuntimeError(f"Docker sandbox execution failed: {exc}") from exc
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except (OSError, RuntimeError):
                    logger.debug("Failed to remove sandbox container", exc_info=True)

        stdout = stdout[: cls.MAX_OUTPUT_BYTES]
        stderr = stderr[: cls.MAX_OUTPUT_BYTES]
        cls.allowed_executions += 1
        cls.last_execution_status = "allowed" if exit_code == 0 else "failed"
        try:
            from core.audit_ledger import AuditLedger
            AuditLedger(workspace_path).record_event(
                "system_call",
                {
                    "sandbox_type": "docker",
                    "code_hash": payload_hash,
                    "status": cls.last_execution_status,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "limits": {
                        "memory": cls.MEMORY_LIMIT,
                        "nano_cpus": cls.CPU_LIMIT,
                        "pids": cls.PIDS_LIMIT,
                        "timeout_seconds": cls.TIMEOUT_SECONDS,
                    },
                },
                tenant_id=tenant_id,
            )
        except (OSError, RuntimeError):
            logger.debug("Unable to write sandbox audit event", exc_info=True)
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "status": "completed" if exit_code == 0 else "error",
        }
