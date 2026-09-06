---
name: qa-handoff
description: Hands reviewed work to QA only after revision, environment, deployment, and publication evidence are verified.
version: 3.0.0
license: MIT
---

# QA Handoff

Prepare a reviewed PR or direct push for QA. This skill may prepare the selected staging environment after the checks below. Production preparation requires explicit authorization for the exact action and target; `qa-mirror` is used only when explicitly selected. This skill never treats a queued merge, Git push, deploy lock, or nonzero row count as proof of readiness.

Announce: “I’m using the qa-handoff skill to hand this off to QA.”

Use `<skill-master-root>/scripts/release_workflow_support.py` (the shared support module lives at the skill-master repository root, not inside the `qa-handoff` skill directory). If it is missing, report `Incomplete` with its expected path and stop.

## Target and configuration

Resolve card and PR/direct revision separately. Read repository instructions and `.claude/skills/qa-handoff.json`. Detect the integration branch, selected target, frontend deployment, API target, Supabase ref, required schema/functions, and relevant configuration as one environment. Never guess a project ref.

For Vetted, staging is `tobsmmjzmlljtyikujlr` and production is `lagvszfwsruniuinxdjb`; verify the staging ref differs from production before any staging migration. Production preparation is outside the default handoff.

## Workflow

### 1. Resolve authority and snapshot

Fetch the complete card thread and current PR metadata. Confirm review/check evidence against the current PR head. For a direct push, require a known `previous..commit` range and verify the commit is on integration; do not call PR-only commands. Revalidate identity and revision before every mutation.

### 2. Read QA history

Normalize and sort comments/events. Preserve historical failures and associate each response with its failure and review-cycle/report identity. Unrelated comments are not responses. Missing written findings produce a targeted clarification request. Use only these dispositions: `established-expectation-correct`, `accepted-deferral`, `fixed`, and `unresolved`; unresolved findings block re-handoff.

### 3. Validate readiness and plan the environment

Check code-review status, required checks, current revision, prerequisites for the entire integration revision being exposed, and deployment configuration. A review that is `Incomplete` cannot produce a complete handoff. An unrelated dirty primary checkout does not block work from a correct isolated snapshot.

For migrations, inspect registry and actual object/definition state first. Apply reviewed files in dependency order through the authorized staging mechanism. Never rewrite SQL by stripping cron statements. Block production-directed side effects, unsafe reruns, partial schema state, and incompatible writer/schema combinations. Coordinate schema and writer deployment, then verify expected definitions or behavior—not just a row count.

Every Edge Function deployment names its project ref and uses the repository’s guarded deploy script. Verify frontend deployment for the selected revision; pushing Git is insufficient. A skipped or unverified prerequisite leaves readiness blocked.

### 4. Merge and prepare the selected target

For PRs, use `--match-head-commit <verified-head>` and confirm actual merged state; queued or auto-merge-enabled is not merged. Do not merge in the primary worktree. For direct pushes, record the verified range and skip merge commands.

For `qa-mirror`, sync only when it was selected. Check both unpromoted history and resulting code trees separately. Ignore only documented deploy-lock bookkeeping paths; verify deployment evidence independently using project, version, source provenance, and behavior. Substantive drift or conflicts remain blocked and are reported exactly.

### 5. Verify behavior

Verify target URL, revision, frontend deployment, API target, Supabase project, schema, functions, configuration, prerequisites, test identity/role, regression checks, and expected behavior. A production-backed preview is not blanket permission to mutate live customer data.

### 6. Publish and mutate card state last

Generate a current testing guide with target URL, revision, prerequisites, identity/role, actions, expected results, regression checks, and failure responses. Reconcile an existing matching publication before posting. Then ensure tester assignment, verify it, move the card to QA last, and read back final card state. Refresh state before every mutation and verify afterward.

Generated comments identify repository, PR/direct revision, and review cycle. If a write is uncertain, re-fetch before retrying; never blindly toggle assignment/column or repeat a comment POST.

### 7. Resume and dry-run

On partial failure, retain completed actions, refresh all state, and resume only missing work. `--dry-run` performs reads and local planning only: no merge, push, deploy, migration, PR-body edit, comment, assignment, or column move. Use `require_dry_run_read_only` to reject mutating command plans.

## Completion rule

Report **QA Handoff Complete** only when all required evidence is present, the selected environment is verified, the current revision is deployed/merged as applicable, the guide is published, assignment and column state are read back, and no blocker remains. Otherwise report **Blocked** or **Partial**, listing completed actions and exact missing evidence. No failed, skipped, queued, stale, or unverified prerequisite can produce completion.

See `references/release-workflow-evidence.md` for the shared evidence and failure semantics.
