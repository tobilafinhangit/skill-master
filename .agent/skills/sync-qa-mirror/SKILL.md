---
name: sync-qa-mirror
description: Syncs the qa-mirror branch (a production-DB-backed preview) with the integration branch and verifies production-parity readiness — reviewed migrations applied, required Edge Functions deployed and verified. Standalone: no Fizzy card, tester assignment, or testing guide involved. Use when the user wants to refresh qa-mirror for ad hoc near-production testing, or is invoked by qa-handoff when qa-mirror is the selected target for a PR handoff.
version: 1.0.0
license: MIT
---

# Sync QA Mirror

Bring `qa-mirror` up to date with the integration branch and prove it is production-parity-ready, so it can be used as a faithful near-production rehearsal surface. This skill's job ends at "qa-mirror is synced and parity-verified" — it does not touch a Fizzy card, assign a tester, or publish a testing guide. `qa-handoff` invokes this skill internally when `qa-mirror` is the explicitly selected target for a PR handoff; it can also be run entirely standalone for ad hoc testing.

**Announce at start:** "I'm using the sync-qa-mirror skill."

**What this skill does NOT do:** it never mutates a Fizzy card, never assigns a tester, never publishes a testing guide, and never applies a non-additive or writer-ambiguous migration to production. A production-backed preview is not blanket permission to mutate live customer data — use demo/internal projects and explicitly scoped test fixtures only when testing against it afterward.

## When to use

- User says "sync qa-mirror", "refresh the mirror", "let me test against near-prod data", or similar, with no PR/card in scope
- `qa-handoff` reaches a step that requires `qa-mirror` as the selected target — it calls this skill and treats its completion state as an input to its own completion rule

## Invocation

```
/sync-qa-mirror              # sync + parity-verify; asks before any production DDL/deploy
/sync-qa-mirror --dry-run    # read-only: resolve refs, build the parity manifest, report — no merge, push, deploy, or migration apply
```

`--dry-run` performs reads and local planning only.

## Workflow

### 1. Resolve context — never guess a ref

`qa-mirror` is a distinct Supabase project from staging — not staging-with-a-different-branch-name. Resolve, from repository instructions (`.claude/rules/working-branch.md` or equivalent), the exact:
- integration branch (`lovable-staging` or equivalent)
- qa-mirror branch name
- staging Supabase project ref
- production Supabase project ref (the one `qa-mirror`'s preview is wired to)

Confirm the staging ref differs from the production ref before touching anything. If any of these cannot be resolved from repository instructions, stop and ask — do not default or guess.

### 2. Build the production-parity manifest

From the exact revision on the integration branch you are about to sync (not a stale local copy — fetch first), enumerate every:
- changed or required database migration
- RPC/function definition change
- RLS policy / grant / permission change
- Edge Function and its `_shared` dependencies
- function configuration or cron setting change
- frontend/API target change

Use the Supabase plugin/MCP for live registry, object-definition, grant, Edge Function, and configuration checks where available.

### 3. Classify and act on each missing production migration

- **Reviewed additive** (`ADD COLUMN`, `CREATE TABLE`, new index, a new reader RPC/policy on a new object): apply through the approved production Dashboard SQL workflow, including its `schema_migrations` registry insert, then read back the registry row and the expected object/definition. Never use raw `execute_sql` or an unguarded CLI apply as a substitute for the repo's production rails.
- **Non-additive, writer-affecting, or ambiguous** (tightened/replaced `CHECK`, dropped/renamed column, backfill, an RPC body a currently-deployed Edge Function still writes against): STOP. Report the exact migration, its dependent writers/functions, and the coordination required. Do not apply it merely to unblock a sync.
- **Staging-only or intentionally deferred**: record the explicit deferral. This only blocks completion if the behavior you're about to test on qa-mirror depends on it — say so if it does.

### 4. Deploy required Edge Functions

For each Edge Function the manifest requires, deploy only from the exact integration-branch revision (use an isolated worktree if needed) via the repository's guarded deploy script (e.g. `scripts/deploy-edge-fn.sh`) — never a raw `npx supabase functions deploy`. Verify: correct production project ref, active version, source provenance, `_shared` dependencies, `verify_jwt` setting, cron/API-key configuration, and a safe runtime smoke check. A version number or a deploy-lock file alone is not evidence of parity.

Schema and writer/function deployment must land together where the change requires both — never apply the migration and defer the writer, or vice versa.

### 5. Merge the sync — in an isolated worktree, never the primary tree

The mandatory cleanup steps in a merge flow (`git restore .` / `git reset` / `git cherry-pick --abort`) are indiscriminate and will destroy uncommitted work sitting in the user's primary working tree. Always:

```bash
git fetch origin --quiet
WT=$(mktemp -d)
git worktree add "$WT" origin/qa-mirror
git -C "$WT" config user.email "tobi@venturefor.africa"
git -C "$WT" config user.name "tobilafinhangit"
git -C "$WT" merge origin/<integration-branch> --no-ff -m "Merge <integration-branch> into qa-mirror"
git -C "$WT" push origin qa-mirror
git worktree remove "$WT"   # if this fails because the worktree contains a submodule
                            # checkout, use `rm -rf "$WT" && git worktree prune` instead
```

Set the worktree's git identity **before** the first commit — a merge commit authored as `claude@vettedai.app` is rejected by Vercel's GitHub integration with an opaque doc-link error, not a real error body.

### 6. Drift check — `git cherry`, never `git merge-base --is-ancestor`

```bash
git fetch origin --quiet
git cherry origin/<integration-branch> origin/qa-mirror
```

`+` lines are content unique to `qa-mirror` that never reached the integration branch. `-` lines are dual-SHA copies already present under a different commit — benign, ignore. `git merge-base --is-ancestor` is the wrong tool here: it false-fires immediately after every normal merge (the merge commit itself is never an ancestor of the other side), so it would flag drift on every clean sync.

Before escalating any `+` result as real drift, disambiguate empty/no-op commits — a `--allow-empty` commit made to poke a missed deploy webhook carries no content and can never "fail to reach" anywhere:

```bash
git show --name-only --format='' <sha> | grep -c .   # 0 files → likely harmless
git show --format='' <sha> | wc -c                   # 0 bytes → confirms it
```

Zero files and zero bytes: note it, move on — do not treat it as drift. Any non-zero result is genuine content unique to `qa-mirror` — report it; do not silently discard or reset over it.

## Completion rule

Report **Synced** only when: the merge is verified pushed to `origin/qa-mirror` (not just attempted), the drift check is clean or every `+` result has been disambiguated as harmless-empty, and every eligible production-parity artifact is accounted for (each migration classified and, where additive, applied-and-read-back; each required Edge Function deployed and verified; each non-additive/deferred item explicitly reported rather than silently skipped).

Otherwise report **Blocked** or **Partial**, listing what completed and the exact missing evidence. No deploy lock, queued migration, or unverified Edge Function version can produce completion.

When invoked by `qa-handoff`, hand back this completion state (Synced/Blocked/Partial + evidence) as-is — `qa-handoff` treats it as a prerequisite input to its own completion rule and does not re-derive it independently.

See `<skill-master-root>/references/release-workflow-evidence.md` for the shared evidence and failure semantics.
