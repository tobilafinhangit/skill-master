import unittest

from scripts.release_workflow_support import EvidenceError, collect_paginated, require_dry_run_read_only


class ReleaseWorkflowScenarioTests(unittest.TestCase):
    def test_api_error_is_not_empty_success(self):
        with self.assertRaises(EvidenceError):
            collect_paginated("/cards", lambda _url: ({"items": []}, 500))

    def test_dry_run_blocks_all_remote_mutations(self):
        for command in (
            "gh pr merge 42 --match-head-commit abc",
            "git push origin lovable-staging",
            "curl -X POST https://app.fizzy.do/cards/1/comments.json",
            "supabase functions deploy fn_example --project-ref staging",
        ):
            with self.subTest(command=command):
                with self.assertRaises(EvidenceError):
                    require_dry_run_read_only([command], dry_run=True)

    def test_dry_run_allows_only_reads(self):
        require_dry_run_read_only(
            ["gh pr view 42 --json headRefOid", "git diff --name-status base..head"],
            dry_run=True,
        )


if __name__ == "__main__":
    unittest.main()
