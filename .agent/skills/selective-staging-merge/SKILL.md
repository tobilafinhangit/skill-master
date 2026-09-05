---
name: selective-staging-merge
description: Prepare a verified selective release candidate from an integration branch while holding back unready work. Never mutates the caller worktree or merges, deploys, or publishes without explicit authorization.
version: 2.0.0
license: MIT
---

# Selective Staging Merge 2.0

Prepare a reproducible release candidate from pinned integration and production
revisions when staging contains work that must not all ship together. This is an
evidence-and-construction workflow, not a shortcut around QA or deployment review.

**Announce at start:** “I’m using the selective-staging-merge skill.”

## Non-negotiable safety contract

- Resolve repository identity from `remote.origin.url`; resolve branch policy from repository instructions. Conflicting identity or ambiguous branches block.
- Fetch and pin exact source/base SHAs before inventory. A failed fetch or ref lookup is `unknown`, never clean.
- Treat `--exclude` as a starting constraint only. Every inventory unit still needs a disposition and revision-specific readiness evidence.
- Use the helper only from an owned worktree. Never checkout, reset, restore, clean, abort, stash, or cherry-pick in the caller’s worktree.
- Never push production, merge a branch/PR, deploy an application, or apply a migration from this workflow. Publication is a separate explicitly authorized operation after `verify` succeeds.
- Do not infer readiness from a title, card column, commit subject, clean `git cherry`, or historical ancestry alone. Unknown ownership, dependencies, migration state, runtime compatibility, or current delivery blocks.

## States and manifest

The helper uses schema `selective-release/2.0`. The manifest records repository identity, source/target branches and SHAs, observation time, every release unit and changed path, exactly one unit disposition, evidence references, card/PR/repository relationships, dependencies, ordered replay operations, candidate/tree SHAs, migration/runtime requirements, verification results, blockers, run id, owned worktree/branch, and recovery stage.

Unit dispositions are mutually exclusive: `include`, `exclude`, `already_present`, or `unknown`. `include` cannot depend on `exclude` or `unknown`. The overall verdict is `ready`, `blocked`, or `incomplete`; only a fully evidenced candidate with verified migration/runtime readiness may be `ready`.

## Workflow

### 1. Resolve and pin context

Read repository instructions first. Resolve exactly one repository, integration branch, production branch, and applicable board/project context. Fetch the relevant remote refs and record:

```text
repository: <owner>/<repo> (remote URL)
integration: <branch> @ <source SHA>
production: <branch> @ <base SHA>
observed_at: <UTC timestamp>
mode: inventory | build | verify | publish
```

If the integration branch or target branch cannot be established, stop.

### 2. Gather evidence and inventory

Read excluded cards’ descriptions and comments. Resolve explicit repository-qualified card↔PR↔commit associations and all required deliverables. Number, title, branch, filename, and keyword matches nominate candidates only; verify the actual PR merge commit and its containment at the pinned revision. Detect later reverts and superseding PRs. A QA-fix item triggers parent-feature investigation; missing parent ownership blocks rather than allowing a known-failing parent to ship.

Run:

```bash
python3 -B scripts/selective_release.py inventory \
  --repo "$REPO" --base "$BASE_SHA" --source "$SOURCE_SHA" \
  --target-branch "$TARGET_BRANCH" --source-branch "$SOURCE_BRANCH" \
  --exclude "$EXCLUDED_UNITS_OR_SHAS" \
  --output selective-release.inventory.json
```

The inventory walks first-parent history from the unique merge base, oldest first. A non-merge commit is one unit. An ordinary two-parent PR merge is one unit with its delta against parent 1 and its constituent commits recorded. Octopus merges and ambiguous ownership/mainline are blocked. A unit mixing included and excluded work is blocked; it is never split automatically.

The optional `--exclude` value is only a starting constraint and accepts unit ids or exact commit SHAs; it is not ticket-readiness evidence. Complete the inventory with dispositions, reasons, evidence, repository-qualified cards/PRs, dependencies, migration/runtime requirements, and blockers. Validate it:

```bash
python3 -B scripts/selective_release.py validate selective-release.json
```

Validation is structural only. Git verification and evidence gates remain required.

### 3. Build once in an owned worktree

The helper creates a unique worktree beneath the repository’s permitted worktree directory and a unique `codex/` release branch from the pinned target SHA. It records ownership only after creation. It replays included ordinary commits and included merge units exactly once (`-m 1` for supported PR merges), preserving real commits and provenance. It does not replay merge constituents separately.

```bash
python3 -B scripts/selective_release.py build \
  --repo "$REPO" selective-release.json
```

A conflict, unexpected empty cherry-pick, occupied path/branch, or command error stops the run. The manifest records the successful prefix and failing operation; the owned worktree is preserved for diagnosis. Recovery defaults to a fresh build.

### 4. Verify readiness and publication boundary

Assess migrations from the resulting base-to-candidate diff, including renamed, modified, and deleted historical migrations. Require prerequisite/schema/runtime compatibility evidence, including dependencies held back with other units. Record production migration state as `verified`, `missing`, `partial/drifted`, or `unknown`; the last two block readiness. Missing migrations need a reviewed deployment sequence, verification, and recovery plan.

Identify the exact candidate source for edge functions and shared imports. Full staging is not an acceptable deployment source for a selective candidate. Run project-appropriate build/tests and targeted acceptance evidence against the constructed candidate, not the original staging checkout. Keep Git preparation, application deployment, and database application as separate states.

Immediately before any authorized publication, refresh both remote refs. If either pin moved, rebuild and re-evidence. Then verify candidate SHA/tree and evidence:

```bash
python3 -B scripts/selective_release.py verify \
  --repo "$REPO" selective-release.json
```

Push, if separately authorized, only the unique candidate branch without force and verify the remote SHA. Create a PR targeting the resolved production branch with the manifest and migration/runtime checklist. Never invoke a merge command or enable auto-merge. On uncertain push/PR responses, inspect remote state before retrying and preserve partial-success state. Recheck refs after publication; stale evidence means leave/convert the PR to draft and report it.

### 5. Cleanup

Cleanup accepts only the exact owned disposable resource, with the owner marker, matching run id, and no unexpected worktree changes. It refuses foreign paths, published resources, dirty candidates, broad globs, and shared temporary snapshots.

```bash
python3 -B scripts/selective_release.py cleanup selective-release.json
```

## Blocked cases

Stop and report when repository identity, branch policy, merge base, ownership, dependencies, constituent/mainline, revision pins, readiness evidence, migration state, runtime compatibility, candidate identity, or publication response is unknown or contradictory. A syntactically valid manifest is never proof of release safety.

## Relationship to merge-to-prod

`merge-to-prod` handles the normal all-ready promotion audit. If staging contains excluded or unreviewed work, it must stop as blocked and hand off to this verified selective workflow. It must not improvise cherry-picks or reuse an old held-back commit list. Every later release performs a fresh inventory and readiness review.

## Tests

From skill-master:

```bash
python3 -B -m unittest discover -s .agent/skills/selective-staging-merge/tests -v
python3 -B -m unittest discover -s .agent/skills/merge-to-prod/tests -v
python3 -B -m unittest discover -s tests -v
```

The selective suite uses real temporary Git repositories and checks trees, ancestry, exit behavior, caller-state preservation, stale pins, merge replay, and cleanup ownership. It requires no sibling skill directories or external writes.
