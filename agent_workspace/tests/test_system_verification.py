import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from skills.system_verification import RunTestsArgs, VerifyWorkspaceArgs, run_tests, verify_workspace

def test_run_tests_success():
    # Mock subprocess.run
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "All 85 tests passed!"
        mock_res.stderr = ""
        mock_run.return_value = mock_res
        
        args = RunTestsArgs(verbose=True)
        result = run_tests(args)
        
        assert "Exit Code: 0" in result
        assert "All 85 tests passed!" in result
        mock_run.assert_called_once_with(
            ["pytest", "-v"],
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            env=os.environ.copy()
        )

def test_run_tests_failure():
    with patch("subprocess.run", side_effect=Exception("Subprocess failed")):
        args = RunTestsArgs(verbose=False)
        result = run_tests(args)
        assert "Error running tests: Subprocess failed" in result

def test_verify_workspace_success():
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "Success"
        mock_res.stderr = ""
        mock_run.return_value = mock_res
        
        args = VerifyWorkspaceArgs(sync_first=True)
        result = verify_workspace(args)
        
        assert "--- sync manifest ---" in result
        assert "--- validate manifest ---" in result
        assert "--- pap_validate ---" in result
        assert mock_run.call_count == 3

def test_verify_workspace_no_sync():
    with patch("subprocess.run") as mock_run:
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "Success"
        mock_res.stderr = ""
        mock_run.return_value = mock_res
        
        args = VerifyWorkspaceArgs(sync_first=False)
        result = verify_workspace(args)
        
        assert "--- sync manifest ---" not in result
        assert "--- validate manifest ---" in result
        assert "--- pap_validate ---" in result
        assert mock_run.call_count == 2
