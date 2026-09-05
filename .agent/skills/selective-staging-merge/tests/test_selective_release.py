#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import selective_release


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=cwd, text=True,
                          capture_output=True, check=check)


class ManifestTests(unittest.TestCase):
    def base_manifest(self):
        return {
            "schema": "selective-release/2.0",
            "repository": {"remote": "github.com/acme/app", "name": "acme/app"},
            "refs": {"source_branch": "staging", "target_branch": "main",
                     "source_sha": "a" * 40, "base_sha": "b" * 40,
                     "observed_at": "2026-09-05T00:00:00Z"},
            "units": [{"id": "u1", "kind": "commit", "commit": "c" * 40,
                       "paths": ["a.txt"], "disposition": "include",
                       "reason": "reviewed", "evidence": ["qa:1"],
                       "dependencies": []}],
            "operations": [], "readiness": {"migration": "verified", "runtime": "verified"},
            "run": {"id": "run-1", "stage": "inventory"}, "verdict": "incomplete",
        }

    def test_manifest_requires_complete_dispositions_and_evidence(self):
        m = self.base_manifest()
        self.assertEqual(selective_release.validate_manifest(m), [])
        m["units"].append({"id": "u2", "kind": "commit", "commit": "d" * 40,
                            "paths": [], "disposition": "unknown", "reason": "",
                            "evidence": [], "dependencies": []})
        errors = selective_release.validate_manifest(m)
        self.assertTrue(any("units[1]" in e and "reason" in e for e in errors), errors)

    def test_excluded_dependency_blocks_include(self):
        m = self.base_manifest()
        m["units"].append({"id": "u2", "kind": "commit", "commit": "d" * 40,
                            "paths": ["b.txt"], "disposition": "exclude",
                            "reason": "pending QA", "evidence": ["card:2"],
                            "dependencies": []})
        m["units"][0]["dependencies"] = ["u2"]
        errors = selective_release.validate_manifest(m)
        self.assertTrue(any("depends" in e for e in errors), errors)

    def test_pins_match_is_exact(self):
        self.assertTrue(selective_release.pins_match(self.base_manifest(), "b" * 40, "a" * 40))
        self.assertFalse(selective_release.pins_match(self.base_manifest(), "c" * 40, "a" * 40))

    def test_ready_requires_all_units_and_candidate_evidence(self):
        m = self.base_manifest()
        m["verdict"] = "ready"
        errors = selective_release.validate_manifest(m)
        self.assertTrue(any("candidate" in e for e in errors), errors)
        m["result"] = {"candidate_sha": "d" * 40, "tree_sha": "e" * 40}
        self.assertEqual(selective_release.validate_manifest(m), [])

    def test_incomplete_manifest_cannot_be_verified(self):
        m = self.base_manifest()
        m["result"] = {"candidate_sha": "d" * 40, "tree_sha": "e" * 40,
                        "worktree": "/missing", "run_id": "run-1"}
        with self.assertRaises(selective_release.ReleaseError):
            selective_release.require_ready(m)


class GitInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "base.txt").write_text("base\n")
        git(self.repo, "add", "base.txt")
        git(self.repo, "commit", "-qm", "base")
        git(self.repo, "branch", "-M", "main")
        git(self.repo, "checkout", "-qb", "staging")

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, name, content, message):
        (self.repo / name).write_text(content)
        git(self.repo, "add", "--", name)
        git(self.repo, "commit", "-qm", message)
        return git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def test_inventory_walks_first_parent_oldest_first_and_records_paths(self):
        first = self.commit("one.txt", "1\n", "one")
        second = self.commit("two.txt", "2\n", "two")
        source = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        units = selective_release.inventory_units(str(self.repo),
                                                  git(self.repo, "rev-parse", "main").stdout.strip(), source)
        self.assertEqual([u["commit"] for u in units], [first, second])
        self.assertEqual(units[0]["paths"], ["one.txt"])

    def test_inventory_manifest_is_complete_and_exclusions_are_applied(self):
        commit = self.commit("one.txt", "1\n", "one")
        source = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        manifest = selective_release.inventory_manifest(
            str(self.repo), git(self.repo, "rev-parse", "main").stdout.strip(), source,
            "main", "staging", exclusions=[commit])
        self.assertEqual(selective_release.validate_manifest(manifest), [])
        self.assertEqual(manifest["units"][0]["disposition"], "exclude")
        self.assertEqual(manifest["refs"]["source_branch"], "staging")

    def test_merge_unit_is_replayed_once_and_lists_constituents(self):
        branch = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "checkout", "-qb", "feature")
        child = self.commit("feature.txt", "feature\n", "feature")
        git(self.repo, "checkout", "-q", "main")
        self.commit("main.txt", "main\n", "main")
        git(self.repo, "merge", "--no-ff", "feature", "-m", "Merge pull request #7 from feature")
        source = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        units = selective_release.inventory_units(str(self.repo), branch, source)
        merges = [u for u in units if u["kind"] == "merge"]
        self.assertEqual(len(merges), 1)
        self.assertIn(child, merges[0]["constituents"])
        self.assertEqual(merges[0]["mainline"], 1)

    def test_nested_merge_is_recorded_as_a_constituent(self):
        branch = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "checkout", "-qb", "feature-a")
        self.commit("a.txt", "a\n", "a")
        git(self.repo, "checkout", "-q", "main")
        self.commit("main-a.txt", "main-a\n", "main-a")
        git(self.repo, "merge", "--no-ff", "feature-a", "-m", "Merge feature-a")
        merge_one = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "checkout", "-qb", "feature-b")
        git(self.repo, "checkout", "-qb", "nested")
        self.commit("nested.txt", "nested\n", "nested")
        git(self.repo, "checkout", "-q", "feature-b")
        self.commit("b.txt", "b\n", "b")
        git(self.repo, "merge", "--no-ff", "nested", "-m", "Merge nested")
        nested_merge = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "--no-ff", "feature-b", "-m", "Merge feature-b")
        source = git(self.repo, "rev-parse", "HEAD").stdout.strip()
        units = selective_release.inventory_units(str(self.repo), branch, source)
        outer = [u for u in units if u["commit"] == source][0]
        self.assertIn(nested_merge, outer["constituents"])


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.worktrees = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "a").write_text("a\n")
        git(self.repo, "add", "a")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        self.worktrees.cleanup()
        self.tmp.cleanup()

    def test_build_never_touches_dirty_caller_and_records_candidate(self):
        (self.repo / "caller.txt").write_text("keep\n")
        (self.repo / "a").write_text("dirty\n")
        before = git(self.repo, "status", "--porcelain").stdout
        commit = selective_release.commit_file(str(self.repo), "candidate", "candidate\n")
        manifest = {"schema": "selective-release/2.0", "repository": {"name": "local"},
                    "refs": {"source_branch": "staging", "target_branch": "main",
                             "source_sha": commit, "base_sha": self.base,
                             "observed_at": "now"},
                    "units": [{"id": "u1", "kind": "commit", "commit": commit,
                               "paths": ["candidate"], "disposition": "include",
                               "reason": "test", "evidence": ["test"], "dependencies": []}],
                    "operations": [], "readiness": {"migration": "verified", "runtime": "verified"},
                    "run": {"id": "test-run", "stage": "inventory"}, "verdict": "incomplete"}
        result = selective_release.build_candidate(str(self.repo), manifest,
                                                   worktree_root=Path(self.worktrees.name))
        self.assertEqual(git(self.repo, "status", "--porcelain").stdout, before)
        self.assertTrue(Path(result["worktree"]).is_dir())
        self.assertEqual(result["candidate_sha"], git(result["worktree"], "rev-parse", "HEAD").stdout.strip())
        selective_release.cleanup_owned(result)
        self.assertFalse(Path(result["worktree"]).exists())

    def test_cleanup_refuses_unowned_worktree(self):
        with self.assertRaises(selective_release.ReleaseError):
            selective_release.cleanup_owned({"worktree": str(self.repo), "owned": True})

    def test_verify_rejects_moved_remote_revision(self):
        commit = selective_release.commit_file(str(self.repo), "candidate", "candidate\n")
        git(self.repo, "update-ref", "refs/remotes/origin/main", self.base)
        git(self.repo, "update-ref", "refs/remotes/origin/staging", commit)
        manifest = {"schema": "selective-release/2.0", "repository": {"name": "local"},
                    "refs": {"source_branch": "staging", "target_branch": "main",
                             "source_sha": commit, "base_sha": self.base,
                             "observed_at": "now"},
                    "units": [{"id": "u1", "kind": "commit", "commit": commit,
                               "paths": ["candidate"], "disposition": "include",
                               "reason": "test", "evidence": ["test"], "dependencies": []}],
                    "operations": [], "readiness": {"migration": "verified", "runtime": "verified"},
                    "run": {"id": "verify-run", "stage": "inventory"}, "verdict": "incomplete"}
        result = selective_release.build_candidate(str(self.repo), manifest,
                                                   worktree_root=Path(self.worktrees.name))
        manifest["result"] = result
        manifest["verdict"] = "ready"
        manifest["refs"]["source_sha"] = self.base
        with self.assertRaises(selective_release.ReleaseError):
            selective_release.verify_candidate(str(self.repo), manifest)
        manifest["refs"]["source_sha"] = commit
        selective_release.cleanup_owned(result)

    def test_cleanup_reports_worktree_removal_failure(self):
        commit = selective_release.commit_file(str(self.repo), "candidate", "candidate\n")
        manifest = {"schema": "selective-release/2.0", "repository": {"name": "local"},
                    "refs": {"source_branch": "staging", "target_branch": "main",
                             "source_sha": commit, "base_sha": self.base,
                             "observed_at": "now"},
                    "units": [{"id": "u1", "kind": "commit", "commit": commit,
                               "paths": ["candidate"], "disposition": "include",
                               "reason": "test", "evidence": ["test"], "dependencies": []}],
                    "operations": [], "readiness": {"migration": "verified", "runtime": "verified"},
                    "run": {"id": "cleanup-run", "stage": "inventory"}, "verdict": "incomplete"}
        result = selective_release.build_candidate(str(self.repo), manifest,
                                                   worktree_root=Path(self.worktrees.name))
        real_run = selective_release._run

        def fail_remove(repo, args, check=True):
            if args[:2] == ["worktree", "remove"]:
                return subprocess.CompletedProcess(["git", *args], 1, "", "remove failed")
            return real_run(repo, args, check=check)

        with mock.patch.object(selective_release, "_run", side_effect=fail_remove):
            with self.assertRaises(selective_release.ReleaseError):
                selective_release.cleanup_owned(result)
        self.assertTrue(Path(result["worktree"]).exists())
        selective_release.cleanup_owned(result)


if __name__ == "__main__":
    unittest.main()
