"""Unit tests for RepositoryInspector and CanonicalPreservationReceipt (Phase 2-A)."""

import os
import shutil
import subprocess
import tempfile
import unittest

from agent_workspace.core.repository import (
    CanonicalPreservationReceipt,
    RepositoryInspector,
    RepositoryProfile,
    DEFAULT_PROTECTED_PATTERNS,
)


class TestRepositoryInspectorP2A(unittest.TestCase):
    """Verifies repository discovery, ecosystem mapping, and canonical preservation receipts."""

    def setUp(self):
        self.inspector = RepositoryInspector()
        self.temp_dir = tempfile.mkdtemp(prefix="las_test_repo_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _init_git_repo(self, path: str) -> str:
        subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Agent"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "agent@test.local"], cwd=path, check=True)

        readme_file = os.path.join(path, "README.md")
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write("# Test Repo\n")

        subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=path, check=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True)
        return commit.stdout.strip()

    def test_inspect_git_repo_ecosystem_detection(self):
        commit = self._init_git_repo(self.temp_dir)

        # Add python and node indicator files
        with open(os.path.join(self.temp_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("[project]\nname = 'demo'\n")
        with open(os.path.join(self.temp_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"name": "demo-ui"}\n')

        profile = self.inspector.inspect(self.temp_dir)
        self.assertIsInstance(profile, RepositoryProfile)
        self.assertEqual(profile.current_branch, "main")
        self.assertEqual(profile.head_commit, commit)
        self.assertIn("python", profile.detected_ecosystems)
        self.assertIn("node", profile.detected_ecosystems)

        # Verify test commands
        test_cmd_names = [t["name"] for t in profile.test_commands]
        self.assertIn("pytest", test_cmd_names)
        self.assertIn("npm-test", test_cmd_names)

        # Verify protected paths
        for pat in DEFAULT_PROTECTED_PATTERNS:
            self.assertIn(pat, profile.protected_paths)

    def test_inspect_invalid_directory_raises(self):
        non_existent = os.path.join(self.temp_dir, "missing_dir")
        with self.assertRaises(FileNotFoundError):
            self.inspector.inspect(non_existent)

        # Empty dir without git
        empty_dir = os.path.join(self.temp_dir, "not_a_repo")
        os.makedirs(empty_dir, exist_ok=True)
        with self.assertRaises(ValueError):
            self.inspector.inspect(empty_dir)

    def test_canonical_preservation_receipt_lifecycle(self):
        self._init_git_repo(self.temp_dir)

        # 1. Generate initial preservation receipt
        receipt = self.inspector.generate_preservation_receipt(self.temp_dir)
        self.assertIsInstance(receipt, CanonicalPreservationReceipt)
        self.assertTrue(receipt.receipt_id.startswith("cpr_"))
        self.assertTrue(receipt.is_preserved)

        # 2. Verify unmodified repo maintains preservation
        verified = self.inspector.verify_preservation(receipt)
        self.assertTrue(verified.is_preserved)

        # 3. Modify a file in the repo
        scratch_file = os.path.join(self.temp_dir, "scratch.txt")
        with open(scratch_file, "w", encoding="utf-8") as f:
            f.write("uncommitted pollution")

        # 4. Verify that pollution is detected and is_preserved becomes False
        polluted = self.inspector.verify_preservation(receipt)
        self.assertFalse(polluted.is_preserved)

        # 5. Clean up the pollution and re-verify preservation
        os.remove(scratch_file)
        restored = self.inspector.verify_preservation(receipt)
        self.assertTrue(restored.is_preserved)


if __name__ == "__main__":
    unittest.main()
