#!/usr/bin/env python3
"""Offline tests for the merge-to-prod 2.0.0 helpers.

Everything here runs with the standard library, no network, no git remote,
no Fizzy. Fixture files live in tests/fixtures/.

Behavior that only manifests against live git, network, or timing (patch
drift vs merge conflicts, closure-timeout readback, changed-head refresh
discipline) is specified in references/scenario-walkthroughs.md — these
tests pin the helper contracts and the presence of that prose, and never
claim text search proves the workflow.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))

import card_refs
import managed_section
import manifest


def fixture(name):
    with open(os.path.join(HERE, "fixtures", name)) as f:
        return f.read()


def fixture_json(name):
    return json.loads(fixture(name))


class ManifestTest(unittest.TestCase):
    def test_ready_manifest_valid(self):
        # Approved ticket, fully evidenced, nothing unmatched.
        self.assertEqual(manifest.validate(fixture_json("manifest_ready.json")), [])

    def test_unrelated_unfinished_feature_blocks_ready(self):
        # Staging carries work with no readiness evidence: verdict ready
        # is rejected and the unreviewed path is named.
        errors = manifest.validate(fixture_json("manifest_blocked_unreviewed.json"))
        self.assertTrue(errors, "expected invalid")
        self.assertTrue(any("unrelated_new_feature" in e for e in errors),
                        errors)

    def test_partial_migration_evidence_blocks_ready(self):
        errors = manifest.validate(fixture_json("manifest_partial_migration.json"))
        self.assertTrue(errors, "expected invalid")
        self.assertTrue(any("20260905000000_add_risk_score.sql" in e for e in errors),
                        errors)

    def test_covered_without_deliverable_invalid(self):
        # Multi-PR ticket with a missing deliverable: covered requires a
        # merge SHA regardless of the overall verdict.
        errors = manifest.validate(fixture_json("manifest_missing_deliverable.json"))
        self.assertTrue(errors, "expected invalid")
        self.assertTrue(any("deliverable" in e for e in errors), errors)

    def test_non_code_complete_must_not_carry_sha(self):
        m = fixture_json("manifest_ready.json")
        m["verdict"] = "blocked"
        m["blockers"] = ["demo"]
        m["cards"] = [{"number": 64, "state": "non_code_complete",
                       "deliverables": [{"repo": "acme/app", "pr": None,
                                         "sha": "d" * 40}],
                       "completion_evidence": "QA full-pass linked"}]
        errors = manifest.validate(m)
        self.assertTrue(any("non_code_complete" in e for e in errors), errors)

    def test_changed_head_invalidates_pins(self):
        m = fixture_json("manifest_ready.json")
        base = "a" * 40
        self.assertTrue(manifest.pins_match(m, base, "b" * 40))
        # Release head advanced after the audit: evidence is stale.
        self.assertFalse(manifest.pins_match(m, base, "e" * 40))
        self.assertFalse(manifest.pins_match(m, "f" * 40, "b" * 40))

    def test_missing_g1_record_rejects_manifest(self):
        # G1 fail-closed: no recorded prospective merge, no manifest — so
        # PR publication (G5) and finalize have nothing valid to consume.
        m = fixture_json("manifest_ready.json")
        self.assertEqual(manifest.validate(m), [])
        del m["merge_check"]
        errors = manifest.validate(m)
        self.assertTrue(errors, "expected invalid without merge_check")
        self.assertTrue(any("merge_check" in e for e in errors), errors)
        # Malformed and stale records fail the same way.
        m = fixture_json("manifest_ready.json")
        m["merge_check"]["status"] = "probably fine"
        self.assertTrue(any("merge_check" in e
                            for e in manifest.validate(m)))
        m = fixture_json("manifest_ready.json")
        m["merge_check"]["head_sha"] = "e" * 40
        errors = manifest.validate(m)
        self.assertTrue(any("stale" in e for e in errors), errors)
        # A conflicted check rejects the manifest: reconcile first.
        m = fixture_json("manifest_ready.json")
        m["merge_check"]["status"] = "conflict"
        m["merge_check"]["merge_exit"] = 1
        errors = manifest.validate(m)
        self.assertTrue(any("conflict" in e for e in errors), errors)


class CardRefsTest(unittest.TestCase):
    def test_managed_bullets_only(self):
        # (#541), Card #644, (from #318) outside bullets must never close.
        self.assertEqual(card_refs.extract_ticket_numbers(fixture("pr_body_managed.md")),
                         [101, 102])

    def test_boundary_12_vs_312_vs_123(self):
        nums = card_refs.extract_ticket_numbers(fixture("pr_body_boundary.md"))
        self.assertEqual(nums, [12, 123])
        self.assertNotIn(312, nums)

    def test_cross_repo_pr_keeps_own_identity(self):
        refs = card_refs.extract_pr_refs(fixture("pr_refs_mixed.txt"), "acme/main")
        by_pr = {(r["repo"], r["pr"]): r for r in refs}
        # The Congrats URL is never resolved as a local PR number.
        self.assertIn(("other/congrats", 45), by_pr)
        self.assertTrue(by_pr[("other/congrats", 45)]["qualified"])
        # The bare #45 inherits the context repo as unqualified.
        self.assertIn(("acme/main", 45), by_pr)
        self.assertFalse(by_pr[("acme/main", 45)]["qualified"])
        self.assertIn(("acme/other", 46), by_pr)

    def test_revert_needs_reevidence(self):
        self.assertTrue(card_refs.mentions_revert(fixture("revert_note.txt")))
        self.assertFalse(card_refs.mentions_revert(fixture("normal_note.txt")))

    def test_legacy_body_extracts_nothing(self):
        # Legacy bodies: never close from number extraction alone.
        self.assertEqual(card_refs.extract_ticket_numbers(fixture("pr_body_legacy.md")), [])


class ManagedSectionTest(unittest.TestCase):
    def test_extract_and_preserve_operator_content(self):
        body = fixture("pr_body_managed.md")
        managed, outside = managed_section.extract_managed(body)
        self.assertIn("### Tickets", managed)
        self.assertIn("hold the announce", outside)
        self.assertIn("Reviewer checklist", outside)

    def test_legacy_detected(self):
        managed, outside = managed_section.extract_managed(fixture("pr_body_legacy.md"))
        self.assertIsNone(managed)
        self.assertIn("DO NOT close #77", outside)

    def test_edited_manifest_is_suspect(self):
        managed, _ = managed_section.extract_managed(fixture("pr_body_edited.md"))
        raw = managed_section.manifest_json_text(managed)
        self.assertIsNotNone(raw)
        with self.assertRaises(ValueError):
            json.loads(raw)

    def test_replace_preserves_operator_notes(self):
        body = fixture("pr_body_edited.md")
        updated = managed_section.replace_managed(body, "### Tickets\n- #101 done")
        self.assertIn("DO NOT close #77", updated)
        self.assertIn("- #101 done", updated)
        # Legacy bodies keep the full original above the new section.
        legacy = fixture("pr_body_legacy.md")
        updated_legacy = managed_section.replace_managed(legacy, "### Tickets\n- #101 done")
        self.assertIn("Hand-written body", updated_legacy)
        self.assertIn("- #101 done", updated_legacy)


class PaginationFixtureTest(unittest.TestCase):
    def test_malformed_page_is_an_error_not_a_short_page(self):
        with self.assertRaises(ValueError):
            json.loads(fixture("pagination_malformed.txt"))

    def test_count_mismatch_blocks(self):
        counts = fixture_json("pagination_mismatch.json")
        self.assertNotEqual(counts["fetched"], counts["total"],
                            "30 of 44 fetched must stop, never audit partial")


class DryRunTest(unittest.TestCase):
    def _cmds(self, name):
        return [l for l in fixture(name).splitlines() if l.strip()]

    def test_clean_plan_passes(self):
        self.assertEqual(manifest.find_mutations(self._cmds("dryrun_clean.txt")), [])

    def test_dirty_plan_flagged(self):
        hits = manifest.find_mutations(self._cmds("dryrun_dirty.txt"))
        self.assertEqual(len(hits), 2)
        self.assertTrue(any("gh pr edit" in h for h in hits), hits)
        self.assertTrue(any("closure.json" in h for h in hits), hits)


class ProseContractTest(unittest.TestCase):
    """Pin that judgment-only cases have walkthroughs (not code proof)."""

    WALKTHROUGH_CASES = (
        "Changed release head",
        "Positive patch drift",
        "Merge-only content",
        "Failed/malformed API",
        "Closure timeout",
        "Dry-run attempting",
    )

    def test_walkthroughs_present(self):
        path = os.path.join(HERE, "..", "references", "scenario-walkthroughs.md")
        with open(path) as f:
            text = f.read()
        for case in self.WALKTHROUGH_CASES:
            self.assertIn(case, text, "walkthrough missing for: %s" % case)


if __name__ == "__main__":
    unittest.main()
