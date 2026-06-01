import os
import sys
import hashlib
import ast
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class SandboxGuard:
    """Safely isolates and executes dynamically generated dynamic tasks, workflow custom scripts, and code blocks under a Zero-Trust policy."""

    BLOCKED_MODULES = {"os", "sys", "subprocess", "shutil", "socket", "urllib", "requests", "ctypes"}
    BLOCKED_BUILTINS = {"eval", "exec", "compile", "open", "input", "globals", "locals", "__import__"}

    total_executions = 0
    blocked_executions = 0
    allowed_executions = 0
    last_execution_status = "none"

    @classmethod
    def execute_safe(cls, workspace_path: str, code_content: str, globals_dict: Dict[str, Any] = None, locals_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes code_content under a restricted, zero-trust sandbox.
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
            raise PermissionError("Security violation: Sandbox execution blocked. Consensus signature verification failed.")

        # 2. Zero-Trust AST Security Audit
        try:
            tree = ast.parse(code_content)
        except SyntaxError as e:
            cls.blocked_executions += 1
            cls.last_execution_status = "failed"
            raise ValueError(f"Syntax error in dynamic code: {e}")

        for node in ast.walk(tree):
            # Block imports of sensitive modules
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in cls.BLOCKED_MODULES:
                        cls.blocked_executions += 1
                        cls.last_execution_status = "blocked"
                        raise PermissionError(f"Security violation: Import of blocked module '{alias.name}' detected.")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in cls.BLOCKED_MODULES:
                    cls.blocked_executions += 1
                    cls.last_execution_status = "blocked"
                    raise PermissionError(f"Security violation: Import from blocked module '{node.module}' detected.")

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

        # 3. Restricted Execution Environment
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

        if globals_dict:
            # Only allow non-blocked keys
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
            
            # Filter out builtins from returned locals
            return {k: v for k, v in sandbox_locals.items() if k != "__builtins__"}
        except Exception as e:
            cls.blocked_executions += 1
            cls.last_execution_status = "failed"
            logger.error("Sandbox execution runtime error: %s", e)
            raise RuntimeError(f"Sandbox runtime execution failed: {e}") from e
