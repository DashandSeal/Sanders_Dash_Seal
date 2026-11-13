"""Verify a Sanders Dash & Seal release source tree before staging.

Usage:
    python3 scripts/verify_release_source.py <source_dir> <commit>
    python3 scripts/verify_release_source.py <source_dir> <commit> --copy-to <dir>

This is the script called by deploy.sh, deploy/install_application.sh,
deploy/sds-bootstrap.sh, run_preflight_checks.sh and deploy/fetch_release.py.
It did not exist in the repository, so every one of those callers failed.

What it verifies, and nothing more:
  * <commit> is a full 40-hex git SHA;
  * <source_dir> is a git work tree whose HEAD is exactly <commit>;
  * the work tree is clean (no modified, staged or untracked files);
  * the files the deploy path requires are present
    (compose.yaml, nginx.conf, backend/platform-source.json).

With --copy-to, the verified tree is copied to the destination directory
(excluding .git, __pycache__ and *.pyc) so the installer stages exactly
the verified source. Exit status is 0 only when every check passes;
otherwise a reason is printed to stderr and the exit status is 1.
Git identity is the only authority claimed here: this does not audit
code correctness, test results, or deployment readiness.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_FILES = ("compose.yaml", "nginx.conf", "backend/platform-source.json")


def fail(message):
    print("RELEASE_SOURCE_NOT_VERIFIED: " + message, file=sys.stderr)
    raise SystemExit(1)


def git(source_dir, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(source_dir), *args],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        fail("git could not run: " + str(error))
    return result


def verify(source_dir, commit):
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
        fail("exact full 40-hex commit SHA required, got: " + repr(commit))
    commit = commit.lower()
    if not source_dir.is_dir():
        fail("source directory does not exist: " + str(source_dir))
    top = git(source_dir, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        fail("not a git work tree: " + str(source_dir))
    head = git(source_dir, "rev-parse", "HEAD")
    if head.returncode != 0 or head.stdout.strip() != commit:
        fail("HEAD is %r, not approved commit %s"
             % (head.stdout.strip(), commit))
    status = git(source_dir, "status", "--porcelain", "--untracked-files=all")
    if status.returncode != 0:
        fail("git status failed in: " + str(source_dir))
    if status.stdout.strip():
        fail("source checkout has drift:\n" + status.stdout)
    for name in REQUIRED_FILES:
        if not (source_dir / name).is_file():
            fail("required file missing: " + name)
    return commit


def copy_verified(source_dir, destination):
    def ignore(directory, names):
        ignored = []
        for name in names:
            if name in (".git", "__pycache__") or name.endswith(".pyc"):
                ignored.append(name)
        return ignored

    if destination.exists() and not destination.is_dir():
        fail("--copy-to destination is not a directory: " + str(destination))
    shutil.copytree(source_dir, destination, ignore=ignore, dirs_exist_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("commit")
    parser.add_argument("--copy-to", type=Path, default=None)
    args = parser.parse_args(argv)
    commit = verify(args.source_dir, args.commit)
    if args.copy_to is not None:
        copy_verified(args.source_dir, args.copy_to)
    print("RELEASE_SOURCE_VERIFIED %s %s" % (args.source_dir, commit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
