import os
import sys
import subprocess
from pydantic import BaseModel, Field

class RunTestsArgs(BaseModel):
    verbose: bool = Field(default=True, description="Whether to run tests in verbose mode.")

class VerifyWorkspaceArgs(BaseModel):
    sync_first: bool = Field(default=True, description="Whether to sync tool manifests before validation.")

def run_tests(args: RunTestsArgs) -> str:
    """Execute the pytest unit test suite and return stdout, stderr, and exit code."""
    cmd = ["pytest"]
    if args.verbose:
        cmd.append("-v")
        
    try:
        # We invoke the pytest executable directly or via python module
        # To be safe across environments, let's search if pytest is available
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            env=os.environ.copy()
        )
        return f"--- pytest results ---\nExit Code: {res.returncode}\n\nStdout:\n{res.stdout}\n\nStderr:\n{res.stderr}"
    except Exception as e:
        return f"Error running tests: {e}"

def verify_workspace(args: VerifyWorkspaceArgs) -> str:
    """Verify contracts, lints, and schemas within the active workspace."""
    python_exe = sys.executable
    outputs = []
    
    try:
        if args.sync_first:
            # 1. sync manifests
            res_sync = subprocess.run(
                [python_exe, "agent_workspace/tool_manifest.py", "sync"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            outputs.append(f"--- sync manifest ---\nExit: {res_sync.returncode}\n{res_sync.stdout}\n{res_sync.stderr}")
            
        # 2. validate manifests
        res_val = subprocess.run(
            [python_exe, "agent_workspace/tool_manifest.py", "validate"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        outputs.append(f"--- validate manifest ---\nExit: {res_val.returncode}\n{res_val.stdout}\n{res_val.stderr}")
        
        # 3. pap_validate static guards
        res_pap = subprocess.run(
            [python_exe, "agent_workspace/pap_validate.py"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        outputs.append(f"--- pap_validate ---\nExit: {res_pap.returncode}\n{res_pap.stdout}\n{res_pap.stderr}")
        
        return "\n\n".join(outputs)
    except Exception as e:
        return f"Error running workspace verification: {e}"
