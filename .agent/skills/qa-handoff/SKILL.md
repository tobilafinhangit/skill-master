---
name: qa-handoff
description: Hands reviewed work to QA only after revision, environment, deployment, and publication evidence are verified.
version: 3.0.0
license: MIT
---

# QA Handoff

Prepare a reviewed PR or direct push for QA. This skill may prepare the selected staging environment after the checks below. Production preparation requires explicit authorization for the exact action and target; `qa-mirror` is used only when explicitly selected. When `qa-mirror` is explicitly selected, production-backed parity preparation is part of this handoff: eligible reviewed migrations and required Edge Functions must be prepared and verified against production before the handoff can complete. This skill never treats a queued merge, Git push, deploy lock, or nonzero row count as proof of readiness.

Announce: “I’m using the qa-handoff skill to hand this off to QA.”

Resolve the shared support module from the physical `skill-master` repository root, not from the installed/symlinked skills directory. The canonical path is `<skill-master-repo>/scripts/release_workflow_support.py`; when resolving `<skill-master-repo>`, first resolve the physical path of this `SKILL.md` and walk up from `.agent/skills/qa-handoff/` to the repository root. Do not assume the installed path (`~/.codex/skills/...`) is the repository root. Use the module's `validate_local_ci_fallback` and `reconcile_ci_result` helpers. If the canonical module is missing, report `Incomplete` with its expected path and stop.

## Target and configuration

Resolve card and PR/direct revision separately. Read repository instructions and `.claude/skills/qa-handoff.json`. Detect the integration branch, explicitly selected target, frontend deployment, API target, Supabase ref, required schema/functions, and relevant configuration as one environment. Never guess a project ref. `staging` and `qa-mirror` are distinct target modes; do not silently substitute one for the other. If `qa-mirror` is not explicitly selected, do not mutate production.

For Vetted, staging is `tobsmmjzmlljtyikujlr` and production is `lagvszfwsruniuinxdjb`; verify the staging ref differs from production before any staging migration. Production preparation is outside the default staging handoff, but is required for an explicitly selected `qa-mirror` handoff after exact target/ref confirmation and authorization.

## Workflow

### 1. Resolve authority and snapshot

Fetch the complete card thread and current PR metadata. Confirm review/check evidence against the current PR head. For a direct push, require a known `previous..commit` range and verify the commit is on integration; do not call PR-only commands. Revalidate identity and revision before every mutation.

### 2. Read QA history

Normalize and sort comments/events. Preserve historical failures and associate each response with its failure and review-cycle/report identity. Unrelated comments are not responses. Missing written findings produce a targeted clarification request. Use only these dispositions: `established-expectation-correct`, `accepted-deferral`, `fixed`, and `unresolved`; unresolved findings block re-handoff.

### 3. Validate readiness and plan the environment

Check code-review status, required checks, current revision, prerequisites for the entire integration revision being exposed, and deployment configuration. A review that is `Incomplete` cannot produce a complete handoff. An unrelated dirty primary checkout does not block work from a correct isolated snapshot.

#### Local CI fallback

Run the repository's documented local fast lane, local production build, and changed-scope
tests before waiting on slow remote checks when possible. Record exact commands, exit
statuses, runtime versions, checkout cleanliness, and the target revision. These results
are supplemental evidence only; they do not replace clean-runner GitHub CI, post-merge
integration checks, deployment verification, migration verification, Edge Function
verification, or environment parity.

If a required GitHub check is still pending after the configured threshold (default: 10
minutes), continue only when the user explicitly selects the local-CI fallback. Mark the
state `local-pass/github-pending`, name the pending check and elapsed time, and preserve
the remote check URL. Never call a pending check passed. A local fallback may support an
explicitly authorized merge, but it cannot complete QA handoff by itself and cannot
bypass any deployment, migration, security, RBAC/RLS, or production-parity prerequisite.
Re-fetch the remote check and reconcile its final result before declaring the handoff
complete.

If the local wrapper fails due to host tooling, run its documented constituent commands
directly where feasible and record the limitation. Do not edit CI, dependencies, or
verification scope to turn a host failure into a false pass.

For migrations, inspect registry and actual object/definition state first. Apply reviewed files in dependency order through the authorized staging mechanism. Never rewrite SQL by stripping cron statements. Block production-directed side effects, unsafe reruns, partial schema state, and incompatible writer/schema combinations. Coordinate schema and writer deployment, then verify expected definitions or behavior—not just a row count.

Every Edge Function deployment names its project ref and uses the repository’s guarded deploy script. Verify frontend deployment for the selected revision; pushing Git is insufficient. A skipped or unverified prerequisite leaves readiness blocked.

For an explicitly selected `qa-mirror`, build a production-parity manifest from the exact reviewed/merged revision before declaring readiness. Include every changed or required migration, RPC/function definition, RLS/grant/permission change, Edge Function and `_shared` dependency, function configuration/cron setting, and frontend/API target. Use the Supabase plugin/MCP for live registry, object-definition, grant, Edge Function, and configuration checks where available; when production DDL is required, use the approved Supabase Dashboard SQL editor and record the exact migration plus `schema_migrations` registry result. Do not use raw `execute_sql` or an unguarded CLI deploy as a substitute for the repository’s production rails.

Classify each missing production migration before acting:

- **Reviewed additive**: apply it in dependency order through the approved production Dashboard SQL workflow, including its registry insert, then read back the registry and expected objects/definitions.
- **Non-additive, writer-affecting, or ambiguous**: stop and report the exact migration, dependent writers/functions, and required coordination. Do not apply it merely to unblock QA.
- **Staging-only or intentionally deferred**: record the explicit deferral and block a `qa-mirror` completion if the card’s tested behavior depends on it.

For each required production Edge Function, deploy only from the exact merged integration revision (use a clean isolated worktree if necessary) via `scripts/deploy-edge-fn.sh`; verify the correct production ref, active version, source provenance, `_shared` dependencies, `verify_jwt`, cron/API-key configuration, and a safe runtime smoke check. A version number, deployment lock, or cross-project source hash alone is not evidence of parity. Schema and writer/function deployment must be coordinated atomically where the change requires both.

### 4. Merge and prepare the selected target

For PRs, use `--match-head-commit <verified-head>` and confirm actual merged state; queued or auto-merge-enabled is not merged. Do not merge in the primary worktree. For direct pushes, record the verified range and skip merge commands.

For `qa-mirror`, sync only when it was selected. Check both unpromoted history and resulting code trees separately. Ignore only documented deploy-lock bookkeeping paths; verify deployment evidence independently using project, version, source provenance, and behavior. Complete the production-parity manifest and its approved preparation steps before syncing/declaring the mirror ready. Substantive code drift, backend drift, missing required migration/function, or conflicts remain blocked and are reported exactly.

### 5. Verify behavior

Verify target URL, revision, frontend deployment, API target, Supabase project, schema, functions, configuration, prerequisites, test identity/role, regression checks, and expected behavior. For `qa-mirror`, verify the live production-backed schema/function/config contract as the actual calling role, including RLS/RBAC denial and allow paths where applicable. A production-backed preview is not blanket permission to mutate live customer data; use demo/internal projects and explicitly scoped test fixtures only.

### 6. Publish and mutate card state last

Generate a current testing guide with target URL, revision, prerequisites, identity/role, actions, expected results, regression checks, and failure responses. Reconcile an existing matching publication before posting. Then ensure tester assignment, verify it, move the card to QA last, and read back final card state. Refresh state before every mutation and verify afterward.

Generated comments identify repository, PR/direct revision, selected target mode, Supabase refs, production-parity actions/evidence, and review cycle. If a write is uncertain, re-fetch before retrying; never blindly toggle assignment/column or repeat a comment POST.

### 7. Resume and dry-run

On partial failure, retain completed actions, refresh all state, and resume only missing work. `--dry-run` performs reads and local planning only: no merge, push, deploy, migration, PR-body edit, comment, assignment, or column move. Use `require_dry_run_read_only` to reject mutating command plans.

## Completion rule

Report **QA Handoff Complete** only when all required evidence is present, the selected environment is verified, the current revision is deployed/merged as applicable, the guide is published, assignment and column state are read back, and no blocker remains. For `qa-mirror`, this additionally requires the production-parity manifest to be complete, every required eligible production artifact to be applied/deployed and verified, and every non-additive/deferred dependency to be proven irrelevant to the tested behavior. Otherwise report **Blocked** or **Partial**, listing completed actions and exact missing evidence. No failed, skipped, queued, stale, or unverified prerequisite can produce completion.

See `<skill-master-root>/references/release-workflow-evidence.md` for the shared evidence and failure semantics.
