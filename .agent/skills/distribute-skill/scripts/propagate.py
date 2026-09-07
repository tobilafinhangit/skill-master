#!/usr/bin/env python3
"""Safely propagate skill-master/main to configured consumer repositories.

Dry-run is the default. Apply mode uses disposable worktrees and never edits
an existing consumer checkout. Direct pushes and PR creation are policy-driven.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

CANONICAL = "/Users/USER/code/repos/skill-master"
POLICIES = {
    "vettedai": {"path": "/Users/USER/code/repos/vettedai-audition-supabase-version", "integration": "lovable-staging", "mode": "direct"},
    "congrats": {"path": "/Users/USER/code/repos/vetted-congrats-Flow-GENEROUS", "integration": "verify-deployments", "mode": "pr"},
    "backend": {"path": "/Users/USER/code/repos/backend-restructing", "integration": "backend-verify-deployment", "mode": "pr"},
    "vfacoffeechat": {"path": "/Users/USER/code/repos/vfacoffeechat", "integration": "main", "mode": "direct"},
    "nts-opportunity-hour-digest": {"path": "/Users/USER/code/repos/nts-opportunity-hour-digest", "integration": "main", "mode": "direct"},
}


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), *args], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=check)


def pointer(repo):
    result = git(repo, "ls-tree", "HEAD", "submodules/skill-master", check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.split()[2]


def inspect_consumer(name, policy):
    repo = Path(policy["path"])
    if not repo.is_dir():
        return {"consumer": name, "status": "missing", "path": str(repo),
                "integration": policy["integration"], "action": policy["mode"]}
    dirty = git(repo, "status", "--porcelain", check=False)
    if dirty.returncode != 0:
        return {"consumer": name, "status": "invalid_repo", "path": str(repo),
                "integration": policy["integration"], "action": policy["mode"]}
    if dirty.stdout:
        return {"consumer": name, "status": "dirty", "path": str(repo),
                "integration": policy["integration"], "action": policy["mode"]}
    return {
        "consumer": name,
        "status": "ready",
        "action": policy["mode"],
        "integration": policy["integration"],
        "old_pointer": pointer(repo),
        "path": str(repo),
    }


def canonical_sha():
    result = git(CANONICAL, "rev-parse", "origin/main^{commit}")
    return result.stdout.strip()


def update_worktree(repo, ref, sha, action=None):
    temp = Path(tempfile.mkdtemp(prefix="skill-propagate-"))
    shutil.rmtree(temp)
    worktree = str(temp)
    try:
        added = git(repo, "worktree", "add", "--detach", worktree, f"origin/{ref}", check=False)
        if added.returncode != 0:
            return {"status": "failed", "error": "worktree creation failed"}
        initialized = git(worktree, "submodule", "update", "--init", "submodules/skill-master", check=False)
        if initialized.returncode != 0:
            return {"status": "failed", "error": "submodule initialization failed"}
        submodule = Path(worktree) / "submodules/skill-master"
        fetched = git(submodule, "fetch", "origin", "main", check=False)
        if fetched.returncode != 0:
            return {"status": "failed", "error": "skill-master fetch failed"}
        checked = git(submodule, "checkout", "--detach", sha, check=False)
        if checked.returncode != 0:
            return {"status": "failed", "error": "skill-master checkout failed"}
        changed = git(worktree, "status", "--porcelain")
        if any(not line.endswith("submodules/skill-master") for line in changed.stdout.splitlines()):
            return {"status": "failed", "error": "worktree has unrelated changes"}
        if not changed.stdout.strip():
            return {"status": "noop", "old_pointer": sha, "new_pointer": sha}
        old_pointer = pointer(worktree)
        if action:
            result = action(worktree)
            result.update({"old_pointer": old_pointer, "new_pointer": sha})
            return result
        return {"status": "updated", "worktree": worktree, "old_pointer": old_pointer, "new_pointer": sha}
    finally:
        git(repo, "worktree", "remove", "--force", worktree, check=False)
        shutil.rmtree(worktree, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="perform commits/pushes/PRs")
    mode.add_argument("--dry-run", action="store_true", help="report planned actions (default)")
    parser.add_argument("--consumer", action="append", choices=sorted(POLICIES), dest="consumers")
    args = parser.parse_args(argv)
    sha = canonical_sha()
    names = args.consumers or list(POLICIES)
    results = {"canonical_sha": sha, "mode": "apply" if args.apply else "dry-run", "consumers": []}
    for name in names:
        result = inspect_consumer(name, POLICIES[name])
        if args.apply and result["status"] in ("ready", "dirty"):
            result.update(apply_consumer(name, POLICIES[name], sha))
        results["consumers"].append(result)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 1 if any(r["status"] in ("failed", "invalid_repo") for r in results["consumers"]) else 0


def apply_consumer(name, policy, sha):
    repo = Path(policy["path"])
    branch = f"codex/skills-{sha[:12]}-{name}"

    def action(worktree):
        if git(worktree, "switch", "-c", branch, check=False).returncode != 0:
            return {"status": "failed", "error": "pointer branch creation failed"}
        if git(worktree, "add", "submodules/skill-master", check=False).returncode != 0:
            return {"status": "failed", "error": "pointer staging failed"}
        if git(worktree, "-c", "user.name=Codex", "-c", "user.email=codex@local",
               "commit", "-m", "chore(skills): bump skill-master", check=False).returncode != 0:
            return {"status": "failed", "error": "pointer commit failed"}
        if policy["mode"] == "direct":
            if git(worktree, "push", "origin", f"HEAD:refs/heads/{policy['integration']}", check=False).returncode != 0:
                return {"status": "failed", "error": "integration branch push rejected"}
            return {"status": "pushed", "branch": policy["integration"],
                    "commit": git(worktree, "rev-parse", "HEAD").stdout.strip()}
        if git(worktree, "push", "origin", f"HEAD:refs/heads/{branch}", check=False).returncode != 0:
            return {"status": "failed", "error": "pointer branch push rejected", "branch": branch}
        pr = subprocess.run(["gh", "pr", "create", "--base", policy["integration"], "--head", branch,
                             "--title", "chore: bump skill-master", "--body", f"Bump skill-master to {sha}."],
                            cwd=worktree, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if pr.returncode != 0:
            return {"status": "failed", "error": "pointer PR creation failed", "branch": branch}
        return {"status": "pr_created", "branch": branch, "pr": pr.stdout.strip()}

    return update_worktree(repo, policy["integration"], sha, action=action)


if __name__ == "__main__":
    sys.exit(main())
