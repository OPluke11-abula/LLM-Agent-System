import os
import subprocess
import sys

ZERO_SHA = "0" * 40


def _block(message: str) -> int:
    print(f"[Git Guard] DANGEROUS OPERATION BLOCKED: {message}", file=sys.stderr)
    print("[Git Guard] To bypass this check, set the environment variable BYPASS_GIT_GUARD=1.", file=sys.stderr)
    return 1


def _is_ancestor(remote_sha: str, local_sha: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", remote_sha, local_sha],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def check_pre_push_records(stdin_payload: str) -> list[str]:
    """Return blocking messages for destructive pre-push hook records."""
    messages = []
    for raw_line in stdin_payload.splitlines():
        fields = raw_line.split()
        if len(fields) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = fields
        if local_sha == ZERO_SHA:
            messages.append(f"Deleting remote ref {remote_ref} is forbidden.")
            continue
        if remote_sha == ZERO_SHA:
            continue
        if not _is_ancestor(remote_sha, local_sha):
            messages.append(f"Non-fast-forward push to {remote_ref} is forbidden.")
    return messages


def check_argv(args: list[str]) -> list[str]:
    args_lower = [arg.lower() for arg in args]
    messages = []

    if "push" in args_lower:
        force_flags = {"-f", "--force", "--force-with-lease"}
        if force_flags.intersection(args_lower) or any(arg.startswith("--force-") for arg in args_lower):
            messages.append("Force pushing is strictly forbidden for automated agents.")

    if "reset" in args_lower and "--hard" in args_lower:
        messages.append("Hard resets ('git reset --hard') are forbidden to prevent erasing uncommitted agent work.")

    if "clean" in args_lower:
        clean_flags = {"-f", "-fd", "-df", "--force"}
        if clean_flags.intersection(args_lower) or any("-f" in arg for arg in args_lower):
            messages.append("Destructive clean operations are forbidden.")

    return messages


def read_stdin_payload() -> str:
    try:
        if not sys.stdin.isatty():
            return sys.stdin.read()
    except OSError:
        return ""
    return ""


def main():
    # Allow human bypass if explicit environment variable is set
    if os.environ.get("BYPASS_GIT_GUARD") == "1":
        sys.exit(0)

    messages = check_argv(sys.argv[1:])
    stdin_payload = read_stdin_payload()
    if stdin_payload.strip():
        messages.extend(check_pre_push_records(stdin_payload))

    if messages:
        sys.exit(_block("; ".join(messages)))

    sys.exit(0)

if __name__ == "__main__":
    main()
