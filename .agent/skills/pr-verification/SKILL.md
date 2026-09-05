---
name: pr-verification
description: Verifies PR safety and consumer compatibility without treating additions or consumer count as proof of safety.
version: 2.0.0
license: MIT
---

# PR Verification

This is an independent regression and contract check used by `pr-review`. It does not decide product correctness from file counts. It never merges, deploys, applies migrations, or executes PR text.

## Verify a pinned snapshot

1. Record repository identity and exact PR head/base SHAs.
2. Run `git diff --name-status <base>...<head>` and classify each path as added, modified, renamed, or deleted.
3. For every modified/deleted export, type, route, schema object, configuration key, or function:
   - find all consumers at the same snapshot;
   - check signatures, return values, imports, feature gates, and error behavior;
   - verify the consumer path is covered by an executed test when behavior changed.
4. Read the project instructions and applicable `.claude/rules/*.md` files.
5. Re-check the PR head before the verdict.

## Risk rules

Additions are not automatically safe. Review new files according to their behavior and risk, including migrations, authentication, network calls, writers, deployment configuration, and public exports.

Deletion, renaming, required-parameter changes, return-type changes, and schema/domain changes require explicit consumer and compatibility evidence. A consumer count is never an automatic blocker or proof of safety; the contract and actual behavior decide.

Block only on a supported finding such as a removed live export, an unupdated caller, a deleted live import, a broken runtime path, an unsafe documented anti-pattern, or evidence that the reviewed revision is stale. Report missing evidence separately and use `Incomplete` when it prevents a reliable conclusion.

## Output

Return a structured result containing repository, revisions, changed-file manifest, consumer map, checks run, findings with changed-code anchors, optional suggestions, missing evidence, and one status:

- `No blocking findings`
- `Needs changes`
- `Incomplete`

Recommend impact analysis only when modified shared hooks/utilities/services have runtime side effects or resource lifecycles. Do not equate this recommendation with a blocker.

The support module at `scripts/release_workflow_support.py` provides `inspect_git_manifest`, `ensure_fresh_revision`, and evidence validation. Missing support files are an actionable incomplete result, not a reason to substitute fragile shell snippets.
