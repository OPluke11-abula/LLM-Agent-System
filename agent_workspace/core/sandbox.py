import os
import sys
import hashlib
import ast
import logging
import tempfile
import shutil
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FileSnapshotTransaction:
    """Manages workspace snapshots and automatically rolls back modified files on failure."""
    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.temp_dir = None

    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp()
        for root, dirs, files in os.walk(self.workspace_path):
            rel_root = os.path.relpath(root, self.workspace_path)
            parts = rel_root.split(os.sep)
            if any(p.startswith('.') or p in ("__pycache__", "node_modules", "venv", ".venv") for p in parts if p and p != '.'):
                continue
            for file in files:
                src_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(src_path, self.workspace_path)
                dst_path = os.path.join(self.temp_dir, rel_file_path)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                try:
                    shutil.copy2(src_path, dst_path)
                except Exception as e:
                    logger.warning("[FileSnapshotTransaction] Failed to snapshot file %s: %s", src_path, e)
        return self

    def rollback(self):
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return
        logger.info("[FileSnapshotTransaction] Initiating rollback for workspace: %s", self.workspace_path)
        
        # 1. Delete all non-ignored files in the workspace
        for root, dirs, files in os.walk(self.workspace_path, topdown=False):
            rel_root = os.path.relpath(root, self.workspace_path)
            parts = rel_root.split(os.sep)
            if any(p.startswith('.') or p in ("__pycache__", "node_modules", "venv", ".venv") for p in parts if p and p != '.'):
                continue
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning("[FileSnapshotTransaction] Failed to delete file during rollback: %s: %s", file_path, e)

        # 2. Restore files from the snapshot
        for root, dirs, files in os.walk(self.temp_dir):
            for file in files:
                src_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(src_path, self.temp_dir)
                dst_path = os.path.join(self.workspace_path, rel_file_path)
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                try:
                    shutil.copy2(src_path, dst_path)
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
    abs_workspace = os.path.abspath(workspace_path)
    
    def safe_open(file, mode='r', *args, **kwargs):
        if isinstance(file, (str, bytes)):
            if isinstance(file, bytes):
                decoded_file = file.decode("utf-8", errors="replace")
            else:
                decoded_file = file
            
            # Resolve to absolute path
            if os.path.isabs(decoded_file):
                resolved_path = os.path.abspath(decoded_file)
            else:
                resolved_path = os.path.abspath(os.path.join(abs_workspace, decoded_file))
                
            try:
                rel = os.path.relpath(resolved_path, abs_workspace)
                if rel.startswith("..") or os.path.isabs(rel):
                    raise PermissionError(f"Security violation: Directory traversal attempt outside workspace boundaries: '{file}'")
            except ValueError:
                raise PermissionError(f"Security violation: Directory traversal attempt outside workspace boundaries: '{file}'")
                
        return open(file, mode, *args, **kwargs)
        
    return safe_open


class SandboxGuard:
    """Safely isolates and executes dynamically generated dynamic tasks, workflow custom scripts, and code blocks under a Zero-Trust policy."""

    BLOCKED_MODULES = {"os", "sys", "subprocess", "shutil", "socket", "urllib", "requests", "ctypes"}
    BLOCKED_BUILTINS = {"eval", "exec", "compile", "open", "input", "globals", "locals", "__import__"}

    total_executions = 0
    blocked_executions = 0
    allowed_executions = 0
    last_execution_status = "none"

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
        """
        Executes code_content under a restricted, zero-trust sandbox.
        Supports 'ast' or 'docker' modes, with graceful fallback.
        Requires signature verification from ProofOfConsensus.
        """
        cls.total_executions += 1
        
        # 1. Consensus Verification
        payload_hash = hashlib.sha256(code_content.encode("utf-8")).hexdigest()
        try:
            from core.discussion_room import ProofOfConsensus
        except ImportError:
            from agent_workspace.core.discussion_room import ProofOfConsensus

        if not ProofOfConsensus.is_consensus_approved(workspace_path, payload_hash):
            cls.blocked_executions += 1
            cls.last_execution_status = "blocked"
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

        # Determine resolved sandbox type and handle Docker checks
        resolved_sandbox_type = sandbox_type.lower()
        if resolved_sandbox_type == "docker":
            docker_available = False
            client = None
            try:
                import docker
                client = docker.from_env()
                client.ping()
                docker_available = True
            except Exception:
                pass
            
            # Check CLI fallback possibility
            docker_cli_available = False
            if not docker_available:
                import subprocess
                try:
                    res = subprocess.run(["docker", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if res.returncode == 0:
                        docker_cli_available = True
                except Exception:
                    pass
            
            if not docker_available and not docker_cli_available:
                logger.warning("[SandboxGuard] Docker sandbox requested but Docker is unavailable. Falling back to AST.")
                resolved_sandbox_type = "ast"

        # 2. Execute Docker Sandbox
        if resolved_sandbox_type == "docker":
            import base64
            import subprocess
            encoded_code = base64.b64encode(code_content.encode("utf-8")).decode("utf-8")
            exit_code = -1
            stdout = ""
            stderr = ""
            
            # Try SDK first
            try:
                import docker
                client = docker.from_env()
                container = client.containers.run(
                    image="python:3.11-slim",
                    command=["sh", "-c", f"echo {encoded_code} | base64 -d | python"],
                    mem_limit="128m",
                    network_mode="none",
                    detach=True,
                    stdout=True,
                    stderr=True
                )
                result = container.wait(timeout=10.0)
                exit_code = result.get("StatusCode", 0)
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8")
                container.remove(force=True)
            except Exception as e:
                logger.warning(f"Docker Python SDK execution failed: {e}. Trying CLI fallback...")
                
            # CLI fallback
            if exit_code == -1:
                try:
                    cmd = [
                        "docker", "run", "--rm",
                        "-m", "128m",
                        "--network", "none",
                        "python:3.11-slim",
                        "sh", "-c", f"echo {encoded_code} | base64 -d | python"
                    ]
                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0)
                    exit_code = res.returncode
                    stdout = res.stdout
                    stderr = res.stderr
                except Exception as err:
                    cls.blocked_executions += 1
                    cls.last_execution_status = "failed"
                    # Log failed run to ledger
                    try:
                        from core.audit_ledger import AuditLedger
                        audit = AuditLedger(workspace_path)
                        audit.record_event("system_call", {
                            "sandbox_type": "docker",
                            "code_hash": payload_hash,
                            "status": "failed",
                            "error": str(err)
                        }, tenant_id=tenant_id)
                    except Exception:
                        pass
                    raise RuntimeError(f"Docker sandbox execution failed (Docker Daemon/CLI unavailable): {err}")

            # Log to audit trail
            try:
                from core.audit_ledger import AuditLedger
                audit = AuditLedger(workspace_path)
                audit.record_event("system_call", {
                    "sandbox_type": "docker",
                    "code_hash": payload_hash,
                    "status": "allowed" if exit_code == 0 else "failed",
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr
                }, tenant_id=tenant_id)
            except Exception:
                pass

            cls.allowed_executions += 1
            cls.last_execution_status = "allowed" if exit_code == 0 else "failed"

            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "status": "completed" if exit_code == 0 else "error"
            }

        # 3. Execute AST Sandbox (AST is resolved_sandbox_type == "ast")
        # Execute safety checks and code within the rollback transaction
        with FileSnapshotTransaction(workspace_path):
            # Zero-Trust AST Security Audit
            try:
                tree = ast.parse(code_content)
            except SyntaxError as e:
                cls.blocked_executions += 1
                cls.last_execution_status = "failed"
                raise ValueError(f"Syntax error in dynamic code: {e}")

            blocked_words = {"socket", "connect", "environ", "getenv", "getaddrinfo", "gethostbyname", "__globals__", "__subclasses__", "__builtins__"}

            for node in ast.walk(tree):
                # Block imports of sensitive modules
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name_parts = alias.name.split('.')
                        if any(part in cls.BLOCKED_MODULES or part in blocked_words for part in name_parts):
                            cls.blocked_executions += 1
                            cls.last_execution_status = "blocked"
                            raise PermissionError(f"Security violation: Import of blocked module '{alias.name}' detected.")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_parts = node.module.split('.')
                        if any(part in cls.BLOCKED_MODULES or part in blocked_words for part in module_parts):
                            cls.blocked_executions += 1
                            cls.last_execution_status = "blocked"
                            raise PermissionError(f"Security violation: Import from blocked module '{node.module}' detected.")
                    for alias in node.names:
                        if alias.name in blocked_words or alias.name.startswith("_"):
                            cls.blocked_executions += 1
                            cls.last_execution_status = "blocked"
                            raise PermissionError(f"Security violation: Import of blocked name '{alias.name}' detected.")

                # Block calls to unsafe builtins or functions
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr

                    if func_name in cls.BLOCKED_BUILTINS:
                        cls.blocked_executions += 1
                        cls.last_execution_status = "blocked"
                        raise PermissionError(f"Security violation: Unsafe call to '{func_name}' detected inside sandbox.")

                # Block unsafe name references
                if isinstance(node, ast.Name):
                    if node.id.startswith("_") or node.id in blocked_words or any(w in node.id.lower() for w in blocked_words):
                        cls.blocked_executions += 1
                        cls.last_execution_status = "blocked"
                        raise PermissionError(f"Security violation: Reference to blocked name '{node.id}' detected inside sandbox.")

                # Block unsafe attribute accesses
                if isinstance(node, ast.Attribute):
                    if node.attr.startswith("_") or node.attr in blocked_words or any(w in node.attr.lower() for w in blocked_words):
                        cls.blocked_executions += 1
                        cls.last_execution_status = "blocked"
                        raise PermissionError(f"Security violation: Access to blocked attribute '{node.attr}' detected inside sandbox.")

                # Block unsafe string constants
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value.lower()
                    for word in blocked_words:
                        if word in val:
                            cls.blocked_executions += 1
                            cls.last_execution_status = "blocked"
                            raise PermissionError(f"Security violation: Blocked string literal containing '{word}' detected.")
                elif hasattr(ast, "Str") and isinstance(node, ast.Str):
                    val = node.s.lower()
                    for word in blocked_words:
                        if word in val:
                            cls.blocked_executions += 1
                            cls.last_execution_status = "blocked"
                            raise PermissionError(f"Security violation: Blocked string literal containing '{word}' detected.")

            # Restricted Execution Environment
            safe_globals = {
                "__builtins__": {
                    k: v for k, v in __builtins__.items()
                    if k not in cls.BLOCKED_BUILTINS and not k.startswith("__")
                }
            }
            
            # Add basic safe objects
            safe_globals.update({
                "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool, "chr": chr,
                "dict": dict, "divmod": divmod, "enumerate": enumerate, "filter": filter,
                "float": float, "format": format, "hash": hash, "hex": hex, "int": int,
                "isinstance": isinstance, "issubclass": issubclass, "iter": iter, "len": len,
                "list": list, "map": map, "max": max, "min": min, "next": next, "oct": oct,
                "ord": ord, "pow": pow, "range": range, "repr": repr, "reversed": reversed,
                "round": round, "set": set, "slice": slice, "sorted": sorted, "str": str,
                "sum": sum, "tuple": tuple, "zip": zip
            })

            # Inject custom safe open builtin wrapper
            safe_globals["__builtins__"]["open"] = make_safe_open(workspace_path)

            if globals_dict:
                for k, v in globals_dict.items():
                    if k not in cls.BLOCKED_BUILTINS:
                        safe_globals[k] = v

            if locals_dict is None:
                locals_dict = {}

            # Compile and execute within isolated namespace
            try:
                compiled_code = compile(code_content, "<sandbox>", "exec")
                sandbox_locals = locals_dict.copy()
                exec(compiled_code, safe_globals, sandbox_locals)
                
                cls.allowed_executions += 1
                cls.last_execution_status = "allowed"
                
                # Log to audit trail
                try:
                    from core.audit_ledger import AuditLedger
                    audit = AuditLedger(workspace_path)
                    audit.record_event("system_call", {
                        "sandbox_type": "ast",
                        "code_hash": payload_hash,
                        "status": "allowed"
                    }, tenant_id=tenant_id)
                except Exception:
                    pass

                return {k: v for k, v in sandbox_locals.items() if k != "__builtins__"}
            except Exception as e:
                cls.blocked_executions += 1
                cls.last_execution_status = "failed"
                logger.error("Sandbox execution runtime error: %s", e)
                try:
                    from core.audit_ledger import AuditLedger
                    audit = AuditLedger(workspace_path)
                    audit.record_event("system_call", {
                        "sandbox_type": "ast",
                        "code_hash": payload_hash,
                        "status": "failed",
                        "error": str(e)
                    }, tenant_id=tenant_id)
                except Exception:
                    pass
                raise RuntimeError(f"Sandbox runtime execution failed: {e}") from e
