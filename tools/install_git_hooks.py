"""Install a ``commit-msg`` hook enforcing the phase commit regex.

The hook rejects any commit message whose first line does not match::

    ^phase [A-Z]\\.\\d+:

Exits 0 after writing the hook. The hook itself is a portable
``#!/usr/bin/env python3`` script so it works on Windows (Git for
Windows ships its own Python) and POSIX hosts. If the embedded Python
is unavailable we fall back to a small POSIX-shell hook that uses
``grep -E`` (Git Bash provides this on Windows).

Usage:
    python tools/install_git_hooks.py [--repo PATH] [--force] [--self-test]
"""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from pathlib import Path


COMMIT_MSG_PATTERN = r"^phase [A-Z]\.\d+: "


# Python-flavoured hook. Path-portable; uses the same regex as below.
HOOK_PY = """\
#!/usr/bin/env python3
import re, sys, pathlib
PATTERN = r"^phase [A-Z]\\.\\d+: "
msg_path = pathlib.Path(sys.argv[1])
text = msg_path.read_text(encoding="utf-8")
first = text.splitlines()[0] if text else ""
if not re.match(PATTERN, first):
    sys.stderr.write(
        "commit-msg hook rejected message.\\n"
        "  first line: " + repr(first) + "\\n"
        "  required pattern: " + PATTERN + "\\n"
    )
    sys.exit(1)
sys.exit(0)
"""

# POSIX-shell fallback used when the Python shebang is unavailable.
HOOK_SH = """\
#!/usr/bin/env sh
msg=$(head -n1 "$1")
echo "$msg" | grep -Eq '^phase [A-Z]\\.[0-9]+: ' || {
    echo "commit-msg hook rejected message." >&2
    echo "  first line: $msg" >&2
    echo "  required pattern: ^phase [A-Z]\\.[0-9]+: " >&2
    exit 1
}
exit 0
"""


def hook_path(repo: Path) -> Path:
    return repo / ".git" / "hooks" / "commit-msg"


def install(repo: Path, *, force: bool = False, sh: bool = False) -> Path:
    target = hook_path(repo)
    if not target.parent.exists():
        raise FileNotFoundError(
            f"git hooks dir missing: {target.parent} (is {repo} a git repo?)"
        )
    if target.exists() and not force:
        raise FileExistsError(
            f"hook already present at {target}; pass --force to overwrite"
        )
    body = HOOK_SH if sh else HOOK_PY
    target.write_text(body, encoding="utf-8")
    # Make executable (POSIX); harmless on Windows.
    try:
        st = target.stat()
        target.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass
    return target


def run_hook_check(message: str) -> tuple[bool, str]:
    """Same logic as the installed hook. Used by tests."""
    first = message.splitlines()[0] if message else ""
    if re.match(COMMIT_MSG_PATTERN, first):
        return True, ""
    return False, f"first line {first!r} does not match {COMMIT_MSG_PATTERN}"


def invoke_hook(hook: Path, message: str, *, msg_path: Path) -> tuple[int, str]:
    """Run the installed hook script against a message file. Returns
    ``(rc, stderr_text)``. Uses ``sys.executable`` for the python hook.
    """
    import subprocess

    msg_path.write_text(message, encoding="utf-8")
    body = hook.read_text(encoding="utf-8")
    if body.startswith("#!/usr/bin/env python3"):
        proc = subprocess.run(
            [sys.executable, str(hook), str(msg_path)],
            capture_output=True, text=True, timeout=15,
        )
    else:
        sh = (
            os.environ.get("SHELL")
            or "sh"
        )
        proc = subprocess.run(
            [sh, str(hook), str(msg_path)],
            capture_output=True, text=True, timeout=15,
        )
    return proc.returncode, proc.stderr


def _self_test() -> int:
    ok, _ = run_hook_check("phase A.1: write SCHEMA_DECISIONS.md\n")
    if not ok:
        print("self-test FAIL: valid msg rejected", file=sys.stderr)
        return 1
    bad, _ = run_hook_check("just a random commit message\n")
    if bad:
        print("self-test FAIL: invalid msg accepted", file=sys.stderr)
        return 1
    print("self-test OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--sh", action="store_true",
                        help="Install POSIX-shell hook instead of Python.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    try:
        target = install(args.repo, force=args.force, sh=args.sh)
    except (FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"installed commit-msg hook at {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
