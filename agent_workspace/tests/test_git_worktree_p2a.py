"""Unit tests for GitWorktreeManager and canonical preservation guarantee (Phase 2-A)."""

import os
import shutil
import subprocess
import tempfile
import unittest

from agent_workspace.core.git_worktree import GitWorktreeManager
from agent_workspace.core.repository import RepositoryInspector


class TestGitWorktreeManagerP2A(unittest.TestCase):
    """Verifies physical worktree isolation, diff extraction, and host zero-pollution invariant."""

    def setUp(self):
        self.temp_root = tempfile.mkdtemp(prefix="las_wt_test_")
        self.repo_dir = os.path.join(self.temp_root, "source_repo")
        os.makedirs(self.repo_dir, exist_ok=True)
        self.worktrees_dir = os.path.join(self.temp_root, "worktrees")

        self.manager = GitWorktreeManager(base_worktrees_dir=self.worktrees_dir)
        self.inspector = RepositoryInspector()

        # Initialize source git repo
        self._init_git_repo(self.repo_dir)

    def tearDown(self):
        if os.path.exists(self.temp_root):
            shutil.rmtree(self.temp_root, ignore_errors=True)

    def _init_git_repo(self, path: str) -> str:
        subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Agent"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "agent@test.local"], cwd=path, check=True)

        readme_file = os.path.join(path, "main.txt")
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write("initial main content\n")

        subprocess.run(["git", "add", "main.txt"], cwd=path, check=True)
        subprocess.run(["git", "commit", "-m", "chore: init main"], cwd=path, check=True)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True)
        return commit.stdout.strip()

    def test_create_worktree_isolation(self):
        # Initial preservation receipt
        receipt = self.inspector.generate_preservation_receipt(self.repo_dir)

        session = self.manager.create_worktree(
            repo_path=self.repo_dir,
            branch_name="feat/agent-work-01",
            base_ref="main",
        )

        self.assertTrue(session.is_isolated)
        self.assertTrue(os.path.isdir(session.worktree_path))
        self.assertNotEqual(session.worktree_path, self.repo_dir)

        # Mutate a file inside worktree
        wt_file = os.path.join(session.worktree_path, "feature.py")
        with open(wt_file, "w", encoding="utf-8") as f:
            f.write("def feature(): pass\n")

        # Verify main repo is NOT contaminated
        main_feature = os.path.join(self.repo_dir, "feature.py")
        self.assertFalse(os.path.exists(main_feature))

        # Main repo preservation receipt still verified
        check_receipt = self.inspector.verify_preservation(receipt)
        self.assertTrue(check_receipt.is_preserved)

        # Cleanup worktree
        success = self.manager.cleanup_worktree(session, remove_branch_on_abort=True)
        self.assertTrue(success)
        self.assertFalse(os.path.exists(session.worktree_path))

    def test_get_diff_and_commit_changes(self):
        session = self.manager.create_worktree(
            repo_path=self.repo_dir,
            branch_name="feat/agent-diff-test",
            base_ref="main",
        )

        # Create changes in worktree
        new_file = os.path.join(session.worktree_path, "code.py")
        with open(new_file, "w", encoding="utf-8") as f:
            f.write("print('hello from worktree')\n")

        diff = self.manager.get_diff(session)
        self.assertIn("code.py", diff)

        # Commit inside worktree
        new_commit = self.manager.commit_changes(session, "feat: implement code in worktree")
        self.assertNotEqual(new_commit, session.base_commit)

        # Main repo branch must still be main at base commit
        main_head = subprocess.run(
            ["git", "-C", self.repo_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(main_head, session.base_commit)

        # Cleanup
        self.manager.cleanup_worktree(session, remove_branch_on_abort=False)

    def test_canonical_preservation_guarantee_end_to_end(self):
        # 1. Capture initial host receipt
        initial_receipt = self.inspector.generate_preservation_receipt(self.repo_dir)

        # 2. Spin up worktree
        session = self.manager.create_worktree(
            repo_path=self.repo_dir,
            branch_name="feat/guaranteed-clean",
            base_ref="main",
        )

        # 3. Simulate intensive agent activity inside worktree
        for i in range(5):
            fpath = os.path.join(session.worktree_path, f"module_{i}.py")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(f"# module {i}\n")

        self.manager.commit_changes(session, "feat: add 5 modules")

        # 4. Teardown worktree
        cleanup_ok = self.manager.cleanup_worktree(session)
        self.assertTrue(cleanup_ok)

        # 5. Verify host repository preservation receipt is 100% PRESERVED
        final_receipt = self.inspector.verify_preservation(initial_receipt)
        self.assertTrue(final_receipt.is_preserved)
        self.assertEqual(final_receipt.final_status_hash, initial_receipt.initial_status_hash)
        self.assertEqual(final_receipt.final_head, initial_receipt.initial_head)


if __name__ == "__main__":
    unittest.main()
