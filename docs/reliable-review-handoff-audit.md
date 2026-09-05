# Reliable review and QA handoff audit

This checklist records the implementation boundary for the staging-first pilot.

| Area | Implemented evidence |
| --- | --- |
| Review statuses | `pr-review` uses only No blocking findings, Needs changes, Incomplete. |
| Freshness | `ensure_fresh_revision` and pre-publication recheck requirement. |
| Pagination | `collect_paginated` follows links and rejects malformed/non-2xx responses. |
| Direct pushes | `resolve_direct_push_context` requires a known range and integration membership. |
| QA failure history | `classify_qa_findings` preserves failure identity and rejects unrelated replies. |
| Git drift | `inspect_git_manifest` separates tree changes from patch-id history drift. |
| Safe publication | HTML escaping and evidence schema are shared by both workflows. |
| Dry-run | `require_dry_run_read_only` rejects merge, push, deploy, migration, and comment mutations. |
| Environment policy | `qa-handoff` requires a verified target; Vetted staging/prod refs are explicit. |
| Rollout boundary | Only Vetted configuration/pin is updated; no wider propagation. |

Known boundary: the helpers validate mechanics and serialize evidence; the skills remain the decision and coordination layer. They do not classify arbitrary SQL, merge, deploy, apply migrations, or resolve contradictory requirements.
