#!/usr/bin/env python3
"""Fail-closed selective release preparation.

This module deliberately owns only local Git reconstruction and manifest
validation. Evidence adapters, deployment, database application, PR creation,
and merging remain operator-controlled workflow steps in SKILL.md.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
import uuid
from pathlib import Path

SCHEMA = "selective-release/2.0"
DISPOSITIONS = {"include", "exclude", "already_present", "unknown"}
HEX40 = set("0123456789abcdef")


class ReleaseError(RuntimeError):
    pass


def _run(repo, args, check=True):
    if not isinstance(args, (tuple, list)) or not all(isinstance(x, str) for x in args):
        raise ReleaseError("Git commands require an argument array")
    p = subprocess.run(["git", *args], cwd=repo, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and p.returncode:
        raise ReleaseError("git %s failed (%s): %s" % (" ".join(args), p.returncode,
                                                       p.stderr.strip()))
    return p


def _git(repo, *args):
    return _run(repo, args).stdout.strip()


def _sha(value):
    return isinstance(value, str) and len(value) == 40 and set(value.lower()) <= HEX40


def _required(mapping, keys, prefix):
    return ["%s.%s is required" % (prefix, key) for key in keys if key not in mapping]


def validate_manifest(manifest):
    """Return structural errors; this is not evidence or Git verification."""
    errors = []
    if not isinstance(manifest, dict):
        return ["manifest must be an object"]
    if manifest.get("schema") != SCHEMA:
        errors.append("schema must be %s" % SCHEMA)
    for key in ("repository", "refs", "units", "operations", "readiness", "run", "verdict"):
        if key not in manifest:
            errors.append("missing top-level field %s" % key)
    refs = manifest.get("refs", {})
    if isinstance(refs, dict):
        errors += _required(refs, ("source_branch", "target_branch", "source_sha", "base_sha", "observed_at"), "refs")
        for key in ("source_sha", "base_sha"):
            if key in refs and not _sha(refs[key]):
                errors.append("refs.%s must be a 40-character SHA" % key)
    else:
        errors.append("refs must be an object")
    if manifest.get("verdict") not in {"ready", "blocked", "incomplete"}:
        errors.append("verdict must be ready, blocked or incomplete")
    units = manifest.get("units")
    if not isinstance(units, list) or not units:
        errors.append("units must be a non-empty list")
        units = []
    by_id = {}
    for i, unit in enumerate(units):
        prefix = "units[%d]" % i
        if not isinstance(unit, dict):
            errors.append(prefix + " must be an object")
            continue
        for key in ("id", "kind", "commit", "paths", "disposition", "reason", "evidence", "dependencies"):
            if key not in unit:
                errors.append("%s.%s is required" % (prefix, key))
        uid = unit.get("id")
        if uid in by_id:
            errors.append("duplicate unit id %s" % uid)
        else:
            by_id[uid] = unit
        if unit.get("kind") not in {"commit", "merge"}:
            errors.append("%s.kind is invalid" % prefix)
        if not _sha(unit.get("commit")):
            errors.append("%s.commit must be a 40-character SHA" % prefix)
        if unit.get("disposition") not in DISPOSITIONS:
            errors.append("%s.disposition is invalid" % prefix)
        if not isinstance(unit.get("paths"), list) or any(not isinstance(p, str) for p in unit.get("paths", [])):
            errors.append("%s.paths must be a list of strings" % prefix)
        if not isinstance(unit.get("dependencies"), list):
            errors.append("%s.dependencies must be a list" % prefix)
        if unit.get("disposition") in {"include", "exclude", "already_present", "unknown"}:
            if not unit.get("reason"):
                errors.append("%s reason is required" % prefix)
            if not isinstance(unit.get("evidence"), list) or not unit.get("evidence"):
                errors.append("%s evidence is required" % prefix)
        for dep in unit.get("dependencies", []):
            if dep not in by_id and not any(x.get("id") == dep for x in units if isinstance(x, dict)):
                errors.append("%s references missing dependency %s" % (prefix, dep))
    for unit in units:
        if not isinstance(unit, dict) or unit.get("disposition") != "include":
            continue
        for dep in unit.get("dependencies", []):
            other = by_id.get(dep)
            if other and other.get("disposition") in {"exclude", "unknown"}:
                errors.append("%s depends on %s with disposition %s" %
                              (unit.get("id"), dep, other.get("disposition")))
    readiness = manifest.get("readiness")
    if not isinstance(readiness, dict):
        errors.append("readiness must be an object")
    elif manifest.get("verdict") == "ready":
        if any(u.get("disposition") == "unknown"
               for u in units if isinstance(u, dict)):
            errors.append("ready verdict requires every unit to have a decided disposition")
        for key in ("migration", "runtime"):
            if readiness.get(key) != "verified":
                errors.append("ready verdict requires readiness.%s=verified" % key)
        result = manifest.get("result", {})
        if not _sha(result.get("candidate_sha")) or not _sha(result.get("tree_sha")):
            errors.append("ready verdict requires candidate and tree SHAs")
    run = manifest.get("run")
    if not isinstance(run, dict) or not run.get("id") or not run.get("stage"):
        errors.append("run.id and run.stage are required")
    return errors


def pins_match(manifest, base_sha, source_sha):
    refs = manifest.get("refs", {})
    return refs.get("base_sha") == base_sha and refs.get("source_sha") == source_sha


def require_ready(manifest):
    errors = validate_manifest(manifest)
    if errors:
        raise ReleaseError("manifest is not ready: " + "; ".join(errors))
    if manifest.get("verdict") != "ready":
        raise ReleaseError("manifest verdict must be ready before verification/publication")
    return True


def _paths(repo, commit, parent=None):
    args = ["diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z"]
    if parent:
        args = ["diff", "--name-only", "-z", "%s^1" % commit, commit]
    else:
        args.append(commit)
    out = _run(repo, args).stdout
    return sorted(x for x in out.split("\0") if x)


def _constituents(repo, commit):
    parents = _git(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]
    if len(parents) != 2:
        return []
    out = _git(repo, "rev-list", "--reverse", "%s..%s" % (parents[0], commit))
    return [sha for sha in out.splitlines() if sha != commit] if out else []


def inventory_units(repo, base_sha, source_sha):
    """Inventory first-parent units oldest-first; raise on ambiguous merge graphs."""
    if not (_sha(base_sha) and _sha(source_sha)):
        raise ReleaseError("inventory requires pinned 40-character revisions")
    merge_bases = _git(repo, "merge-base", "--all", base_sha, source_sha).splitlines()
    if len(merge_bases) != 1:
        raise ReleaseError("no unique merge base")
    merge_base = merge_bases[0]
    commits = _git(repo, "rev-list", "--first-parent", "--reverse", "%s..%s" % (merge_base, source_sha))
    units = []
    for commit in commits.splitlines():
        parents = _git(repo, "rev-list", "--parents", "-n", "1", commit).split()[1:]
        if len(parents) > 2:
            raise ReleaseError("octopus merge is unsupported: %s" % commit)
        kind = "merge" if len(parents) == 2 else "commit"
        paths = _paths(repo, commit, commit if kind == "merge" else None)
        units.append({"id": "unit-%s" % commit[:12], "kind": kind, "commit": commit,
                      "parents": parents, "mainline": 1 if kind == "merge" else None,
                      "constituents": _constituents(repo, commit) if kind == "merge" else [],
                      "paths": paths, "disposition": "unknown", "reason": "",
                      "evidence": [], "dependencies": []})
    return units


def inventory_manifest(repo, base_sha, source_sha, target_branch, source_branch,
                       exclusions=()):
    """Create a complete, intentionally incomplete manifest from Git inventory."""
    units = inventory_units(repo, base_sha, source_sha)
    excluded = set(exclusions)
    known = {value for unit in units for value in (unit["id"], unit["commit"])}
    unknown_exclusions = excluded - known
    if unknown_exclusions:
        raise ReleaseError("exclusions did not match release units: %s" %
                           ", ".join(sorted(unknown_exclusions)))
    for unit in units:
        if unit["id"] in excluded or unit["commit"] in excluded:
            unit.update({"disposition": "exclude", "reason": "operator exclusion",
                         "evidence": ["git:%s" % unit["commit"]]})
        else:
            unit.update({"reason": "inventory requires evidence classification",
                         "evidence": ["git:%s" % unit["commit"]]})
    remote = _run(repo, ["config", "--get", "remote.origin.url"], check=False).stdout.strip()
    repository = remote or _git(repo, "rev-parse", "--show-toplevel")
    now = _dt.datetime.now(_dt.timezone.utc).isoformat()
    return {"schema": SCHEMA,
            "repository": {"remote": remote, "name": repository},
            "refs": {"source_branch": source_branch, "target_branch": target_branch,
                     "source_sha": source_sha, "base_sha": base_sha,
                     "observed_at": now},
            "units": units, "operations": [],
            "readiness": {"migration": "unknown", "runtime": "unknown"},
            "blockers": ["release units require evidence classification"],
            "run": {"id": "inventory-%s" % uuid.uuid4().hex, "stage": "inventory"},
            "verdict": "incomplete"}


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise ReleaseError("cannot read manifest %s: %s" % (path, exc))


def commit_file(repo, name, content):
    path = Path(repo) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    _run(repo, ["add", "--", name])
    _run(repo, ["commit", "-m", "candidate: %s" % name])
    return _git(repo, "rev-parse", "HEAD")


def _owner_marker(worktree, run_id, branch):
    marker = Path(worktree) / ".selective-release-owner.json"
    write_json(marker, {"schema": SCHEMA, "run_id": run_id, "branch": branch,
                        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat()})
    return marker


def build_candidate(repo, manifest, worktree_root=None):
    errors = validate_manifest(manifest)
    if errors:
        raise ReleaseError("invalid manifest: " + "; ".join(errors))
    if manifest.get("verdict") == "blocked":
        raise ReleaseError("blocked manifest cannot be built")
    refs = manifest["refs"]
    root = Path(worktree_root or (Path(repo) / ".claude" / "worktrees"))
    root.mkdir(parents=True, exist_ok=True)
    run_id = manifest["run"]["id"]
    suffix = uuid.uuid4().hex[:10]
    worktree = root / ("selective-release-%s-%s" % (refs["base_sha"][:12], suffix))
    branch = "codex/selective-release-%s-%s" % (run_id, suffix)
    if worktree.exists():
        raise ReleaseError("worktree path is occupied: %s" % worktree)
    if _run(repo, ["show-ref", "--verify", "--quiet", "refs/heads/%s" % branch], check=False).returncode == 0:
        raise ReleaseError("release branch is occupied: %s" % branch)
    _run(repo, ["worktree", "add", "-b", branch, str(worktree), refs["base_sha"]])
    _owner_marker(worktree, run_id, branch)
    successful = []
    source_result = []
    try:
        for unit in manifest["units"]:
            if unit["disposition"] != "include":
                continue
            if unit["kind"] == "merge":
                args = ["cherry-pick", "-x", "-m", str(unit.get("mainline", 1)), "--no-edit", unit["commit"]]
            else:
                args = ["cherry-pick", "-x", "--no-edit", unit["commit"]]
            result = _run(str(worktree), args, check=False)
            if result.returncode:
                _run(str(worktree), ["cherry-pick", "--abort"], check=False)
                raise ReleaseError("replay failed after %d units (%s): %s" %
                                   (len(successful), unit["id"], result.stderr.strip()))
            successful.append(unit["id"])
            source_result.append({"unit": unit["id"], "source_sha": unit["commit"],
                                  "result_sha": _git(str(worktree), "rev-parse", "HEAD")})
        candidate = _git(str(worktree), "rev-parse", "HEAD")
        tree = _git(str(worktree), "rev-parse", "HEAD^{tree}")
        manifest["operations"] = successful
        manifest["result"] = {"candidate_sha": candidate, "tree_sha": tree,
                               "worktree": str(worktree), "branch": branch,
                               "run_id": run_id,
                               "successful_prefix": successful, "source_result": source_result,
                               "stage": "built"}
        manifest["run"]["stage"] = "built"
        return manifest["result"]
    except Exception:
        manifest.setdefault("result", {})
        manifest["result"].update({"worktree": str(worktree), "branch": branch,
                                    "run_id": run_id, "successful_prefix": successful,
                                    "source_result": source_result,
                                    "failing_unit": unit.get("id") if 'unit' in locals() else None,
                                    "error": str(sys.exc_info()[1]), "stage": "build_failed"})
        manifest["run"]["stage"] = "build_failed"
        raise


def verify_candidate(repo, manifest):
    require_ready(manifest)
    result = manifest.get("result", {})
    worktree = result.get("worktree")
    if not worktree or not Path(worktree).is_dir():
        raise ReleaseError("owned candidate worktree is missing")
    current_base = _git(repo, "rev-parse", "refs/remotes/origin/%s" % manifest["refs"]["target_branch"])
    current_source = _git(repo, "rev-parse", "refs/remotes/origin/%s" % manifest["refs"]["source_branch"])
    if not pins_match(manifest, current_base, current_source):
        raise ReleaseError("source or target moved since inventory")
    candidate = _git(worktree, "rev-parse", "HEAD")
    tree = _git(worktree, "rev-parse", "HEAD^{tree}")
    if candidate != result.get("candidate_sha") or tree != result.get("tree_sha"):
        raise ReleaseError("candidate changed after construction")
    manifest["run"]["stage"] = "verified"
    manifest["verification"] = {"source_sha": current_source, "base_sha": current_base,
                                 "candidate_sha": candidate, "tree_sha": tree,
                                 "verified_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                                 "publication": "not performed"}
    return manifest["verification"]


def cleanup_owned(result):
    worktree = Path(result.get("worktree", ""))
    if result.get("published"):
        raise ReleaseError("refusing cleanup of published resource")
    if not result.get("owned") and not worktree.name.startswith("selective-release-"):
        raise ReleaseError("refusing cleanup of unowned path")
    marker = worktree / ".selective-release-owner.json"
    if not marker.is_file():
        raise ReleaseError("owner marker missing")
    try:
        owner = read_json(marker)
    except ReleaseError:
        raise
    if owner.get("schema") != SCHEMA or owner.get("run_id") != result.get("run_id"):
        raise ReleaseError("owner marker does not match run")
    dirty = []
    for line in _run(str(worktree), ["status", "--porcelain"], check=False).stdout.splitlines():
        if line[3:] != ".selective-release-owner.json":
            dirty.append(line)
    if dirty:
        raise ReleaseError("refusing cleanup of changed candidate worktree")
    repo = _git(str(worktree), "rev-parse", "--git-common-dir")
    common = Path(repo)
    if not common.is_absolute():
        common = (worktree / common).resolve()
    main_repo = common.parent
    branch = owner.get("branch")
    removed = _run(str(main_repo), ["worktree", "remove", "--force", str(worktree)], check=False)
    if removed.returncode:
        raise ReleaseError("owned worktree removal failed: %s" % removed.stderr.strip())
    if branch:
        deleted = _run(str(main_repo), ["branch", "-D", branch], check=False)
        if deleted.returncode:
            raise ReleaseError("owned branch removal failed: %s" % deleted.stderr.strip())


def _parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--repo", required=True)
    inv.add_argument("--base", required=True)
    inv.add_argument("--source", required=True)
    inv.add_argument("--target-branch", required=True)
    inv.add_argument("--source-branch", required=True)
    inv.add_argument("--exclude", default="",
                     help="comma-separated unit ids or commit SHAs to exclude initially")
    inv.add_argument("--output", required=True)
    val = sub.add_parser("validate")
    val.add_argument("manifest")
    build = sub.add_parser("build")
    build.add_argument("--repo", required=True)
    build.add_argument("manifest")
    verify = sub.add_parser("verify")
    verify.add_argument("--repo", required=True)
    verify.add_argument("manifest")
    clean = sub.add_parser("cleanup")
    clean.add_argument("manifest")
    return p


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command == "inventory":
        exclusions = [item.strip() for item in args.exclude.split(",") if item.strip()]
        data = inventory_manifest(args.repo, args.base, args.source,
                                  args.target_branch, args.source_branch, exclusions)
        write_json(args.output, data)
        return 0
    manifest = read_json(args.manifest)
    if args.command == "validate":
        errors = validate_manifest(manifest)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 2
        print("valid")
        return 0
    try:
        if args.command == "build":
            build_candidate(args.repo, manifest)
        elif args.command == "verify":
            verify_candidate(args.repo, manifest)
        elif args.command == "cleanup":
            cleanup_owned(manifest.get("result", {}))
        write_json(args.manifest, manifest)
        return 0
    except ReleaseError as exc:
        if args.command == "build" and isinstance(manifest, dict):
            write_json(args.manifest, manifest)
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
