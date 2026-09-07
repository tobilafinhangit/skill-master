import json
import unittest

from scripts.release_workflow_support import (
    EvidenceError,
    build_evidence_record,
    classify_qa_findings,
    collect_paginated,
    ensure_fresh_revision,
    html_escape,
    inspect_git_manifest,
    require_complete_evidence,
    resolve_direct_push_context,
    require_dry_run_read_only,
    run_git,
    reconcile_ci_result,
    validate_local_ci_fallback,
)


class ReleaseWorkflowSupportTests(unittest.TestCase):
    def test_collect_paginated_follows_next_links_and_rejects_error(self):
        pages = {
            "/comments": ({"items": [{"id": 1}], "next": "/comments?page=2"}, 200),
            "/comments?page=2": ({"items": [{"id": 2}], "next": None}, 200),
        }

        def get(url):
            return pages[url]

        self.assertEqual(collect_paginated("/comments", get), [{"id": 1}, {"id": 2}])

        def failed(_url):
            return {"items": []}, 503

        with self.assertRaises(EvidenceError):
            collect_paginated("/comments", failed)

    def test_collect_paginated_supports_fizzy_array_pages_and_link_headers(self):
        pages = {
            "/cards": ([{"id": 1}], 200, {"Link": '</cards?page=2>; rel="next"', "X-Total-Count": "2"}),
            "/cards?page=2": ([{"id": 2}], 200, {"X-Total-Count": "2"}),
        }
        self.assertEqual(collect_paginated("/cards", lambda url: pages[url]), [{"id": 1}, {"id": 2}])

    def test_direct_push_requires_known_range_and_integration_membership(self):
        self.assertEqual(
            resolve_direct_push_context(
                commit="abc123",
                previous_commit="000111",
                integration_branch="lovable-staging",
                contains_commit=True,
            )["range"],
            "000111..abc123",
        )
        with self.assertRaises(EvidenceError):
            resolve_direct_push_context("abc123", None, "lovable-staging", True)
        with self.assertRaises(EvidenceError):
            resolve_direct_push_context("abc123", "000111", "lovable-staging", False)

    def test_revision_must_match_before_publication(self):
        ensure_fresh_revision("head-a", "head-a")
        with self.assertRaises(EvidenceError):
            ensure_fresh_revision("head-a", "head-b")

    def test_qa_findings_preserve_history_and_block_unresolved(self):
        findings = classify_qa_findings(
            [
                {"id": "fail-1", "kind": "failure", "body": "button is broken"},
                {"id": "noise", "kind": "comment", "body": "thanks"},
                {"id": "reply", "kind": "response", "body": "fixed"},
            ],
            response_dispositions={"fail-1": ("reply", "fixed")},
        )
        self.assertEqual(findings[0]["disposition"], "fixed")
        self.assertTrue(all(item["disposition"] != "unresolved" for item in findings))

        unresolved = classify_qa_findings(
            [{"id": "fail-2", "kind": "failure", "body": "still broken"}],
            response_dispositions={},
        )
        self.assertEqual(unresolved[0]["disposition"], "unresolved")

    def test_evidence_record_is_versioned_and_required_fields_are_validated(self):
        record = build_evidence_record(
            repository="org/repo",
            pr_number=42,
            head_sha="head",
            base_sha="base",
            card_ids=["F-10", "F-11"],
            environment={"name": "staging", "project_ref": "stage-ref"},
        )
        self.assertEqual(record["schema_version"], 1)
        require_complete_evidence(record, required=("repository", "head_sha", "environment"))
        with self.assertRaises(EvidenceError):
            require_complete_evidence(record)
        with self.assertRaises(EvidenceError):
            require_complete_evidence({"repository": "org/repo"}, required=("repository", "head_sha"))

    def test_git_manifest_separates_tree_and_history_drift(self):
        manifest = inspect_git_manifest(
            name_status="A\tnew.py\nM\told.py\nD\tgone.py\n",
            cherry_output="- old commit\n+ unpromoted commit\n",
        )
        self.assertEqual(manifest["added"], ["new.py"])
        self.assertEqual(manifest["modified"], ["old.py"])
        self.assertEqual(manifest["deleted"], ["gone.py"])
        self.assertEqual(manifest["history_drift"], ["unpromoted commit"])

    def test_local_ci_fallback_requires_complete_advisory_evidence(self):
        github = {"run_id": "run-1", "status": "in_progress", "observed_at": "2026-09-07T20:00:00Z"}
        local = {
            "commit_sha": "head",
            "clean_tree": True,
            "timeout_minutes": 10,
            "node_version": "v22.0.0",
            "install_mode": "npm ci --ignore-scripts",
            "commands": [{"command": "npm run build", "status": "passed"}],
        }
        evidence = validate_local_ci_fallback(expected_head_sha="head", github=github, local=local)
        self.assertEqual(evidence["state"], "local-pass/github-pending")
        self.assertEqual(reconcile_ci_result(evidence, head_sha="head", github_status="success")["state"], "github-reconciled")

        cases = (
            {**local, "clean_tree": False},
            {**local, "commit_sha": "stale"},
            {**local, "node_version": ""},
            {**local, "commands": [{"command": "npm run build", "status": "failed"}]},
        )
        for invalid in cases:
            with self.subTest(invalid=invalid):
                with self.assertRaises(EvidenceError):
                    validate_local_ci_fallback(expected_head_sha="head", github=github, local=invalid)

        with self.assertRaises(EvidenceError):
            validate_local_ci_fallback(
                expected_head_sha="head",
                github={**github, "status": "success"},
                local=local,
            )
        with self.assertRaises(EvidenceError):
            validate_local_ci_fallback(
                expected_head_sha="head",
                github=github,
                local={**local, "substitutes_for": ["migration"]},
            )

    def test_html_escape_and_dry_run_guard(self):
        self.assertEqual(html_escape('<script>&"'), "&lt;script&gt;&amp;&quot;")
        require_dry_run_read_only(["git diff", "gh pr view"] , dry_run=True)
        with self.assertRaises(EvidenceError):
            require_dry_run_read_only(["git push"], dry_run=True)
        for command in (
            "gh pr comment 42 --body ok",
            "curl --request POST https://example.test",
            "git -C repo push origin main",
            "supabase db push",
        ):
            with self.subTest(command=command):
                with self.assertRaises(EvidenceError):
                    require_dry_run_read_only([command], dry_run=True)

    def test_run_git_rejects_mutating_subcommands_and_option_injection(self):
        with self.assertRaises(EvidenceError):
            run_git(("push", "origin", "main"), cwd=".")
        with self.assertRaises(EvidenceError):
            run_git(("-c", "core.sshCommand=evil", "show"), cwd=".")


if __name__ == "__main__":
    unittest.main()
