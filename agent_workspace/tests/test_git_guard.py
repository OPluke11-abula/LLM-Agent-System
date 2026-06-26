import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from scripts import git_guard


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "git_guard.py"


def run_guard(
    *args: str,
    stdin: str = "",
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        text=True,
        capture_output=True,
        env=command_env,
        cwd=cwd,
        check=False,
    )


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def write_commit(repo: Path, filename: str, content: str, message: str) -> str:
    path = repo / filename
    path.write_text(content, encoding="utf-8")
    git(repo, "add", filename)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def test_blocks_force_push_argv():
    result = run_guard("git", "push", "--force-with-lease")

    assert result.returncode == 1
    assert "Force pushing is strictly forbidden" in result.stderr


def test_blocks_hard_reset_argv():
    result = run_guard("git", "reset", "--hard")

    assert result.returncode == 1
    assert "Hard resets" in result.stderr


def test_blocks_clean_force_argv():
    result = run_guard("git", "clean", "-fd")

    assert result.returncode == 1
    assert "Destructive clean operations" in result.stderr


def test_allows_bypass_env():
    result = run_guard("git", "reset", "--hard", env={"BYPASS_GIT_GUARD": "1"})

    assert result.returncode == 0
    assert result.stderr == ""


def test_blocks_pre_push_non_fast_forward_record():
    payload = "refs/heads/main bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb refs/heads/main aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"

    with patch("scripts.git_guard._is_ancestor", return_value=False):
        messages = git_guard.check_pre_push_records(payload)

    assert messages == ["Non-fast-forward push to refs/heads/main is forbidden."]


def test_allows_pre_push_fast_forward_record():
    payload = "refs/heads/main bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb refs/heads/main aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"

    with patch("scripts.git_guard._is_ancestor", return_value=True):
        messages = git_guard.check_pre_push_records(payload)

    assert messages == []


def test_blocks_pre_push_remote_delete_record():
    payload = "delete 0000000000000000000000000000000000000000 refs/heads/main aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"

    messages = git_guard.check_pre_push_records(payload)

    assert messages == ["Deleting remote ref refs/heads/main is forbidden."]


def test_pre_push_stdin_allows_fast_forward_in_real_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    base_sha = write_commit(repo, "file.txt", "base", "base")
    local_sha = write_commit(repo, "file.txt", "local", "local")
    payload = f"refs/heads/main {local_sha} refs/heads/main {base_sha}\n"

    result = run_guard(stdin=payload, cwd=repo)

    assert result.returncode == 0
    assert result.stderr == ""


def test_pre_push_stdin_blocks_non_fast_forward_in_real_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test User")
    write_commit(repo, "file.txt", "base", "base")
    git(repo, "checkout", "-b", "remote-side")
    remote_sha = write_commit(repo, "file.txt", "remote", "remote")
    git(repo, "checkout", "-b", "local-side", "master")
    local_sha = write_commit(repo, "file.txt", "local", "local")
    payload = f"refs/heads/main {local_sha} refs/heads/main {remote_sha}\n"

    result = run_guard(stdin=payload, cwd=repo)

    assert result.returncode == 1
    assert "Non-fast-forward push to refs/heads/main is forbidden." in result.stderr
