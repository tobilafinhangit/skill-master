#!/usr/bin/env python3
"""Run the pinned merge-to-prod G1 check and atomically write its record.

The record is evidence only. Consumers must still re-check the live refs and
compare the recorded pins and output hash before publishing.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=check)


def sha256_index(repo):
    tree = git(repo, "write-tree").stdout.strip()
    listing = git(repo, "ls-tree", "-r", "-z", tree).stdout.encode()
    return hashlib.sha256(listing).hexdigest()


def atomic_write(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(record, stream, sort_keys=True, indent=2)
            stream.write("\n")
        os.replace(temp, path)
    except Exception:
        try:
            os.unlink(temp)
        except FileNotFoundError:
            pass
        raise


def ref_tip(repo, ref):
    result = git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def conflict_paths(repo):
    result = git(repo, "diff", "--name-only", "--diff-filter=U", check=False)
    return sorted(p for p in result.stdout.splitlines() if p)


def run(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    output = Path(args.output).resolve()
    worktree = None
    record = None
    try:
        if not re_full_sha(args.base) or not re_full_sha(args.head):
            return 2
        if args.base == args.head:
            return 2
        if ref_tip(repo, args.base_ref) != args.base:
            return 2
        if ref_tip(repo, args.head_ref) != args.head:
            return 2
        if git(repo, "rev-parse", "--show-toplevel", check=False).returncode != 0:
            return 2

        worktree_parent = repo / ".claude" / "worktrees"
        worktree_parent.mkdir(parents=True, exist_ok=True)
        worktree = Path(tempfile.mkdtemp(prefix="mtp-merge-check-",
                                         dir=worktree_parent))
        shutil.rmtree(worktree)
        added = git(repo, "worktree", "add", "--detach", str(worktree), args.base,
                    check=False)
        if added.returncode != 0:
            return 2

        merged = git(worktree, "merge", "--no-commit", "--no-ff", args.head,
                     check=False)
        status = "clean" if merged.returncode == 0 else "conflict"
        record = {
            "base_sha": args.base,
            "head_sha": args.head,
            "worktree": str(worktree.relative_to(repo)),
            "merge_exit": merged.returncode,
            "status": status,
            "conflict_paths": conflict_paths(worktree) if status == "conflict" else [],
            "output_sha256": sha256_index(worktree) if status == "clean" else None,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except (OSError, ValueError, subprocess.SubprocessError):
        return 2
    finally:
        if worktree is not None and worktree.exists():
            removed = git(repo, "worktree", "remove", "--force", str(worktree),
                          check=False)
            if removed.returncode != 0:
                record = None
                return_code = 2
            else:
                return_code = None
        else:
            return_code = None

    if record is None:
        return 2
    try:
        atomic_write(output, record)
    except OSError:
        return 2
    return return_code if return_code is not None else (0 if record["status"] == "clean" else 1)


def re_full_sha(value):
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
