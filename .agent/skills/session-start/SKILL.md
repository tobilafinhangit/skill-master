---
name: session-start
description: Use when beginning a coding, debugging, review, or deployment task. Grounds the agent in the current branch, instruction harness, existing implementation, and overlapping work before edits.
version: 1.0.0
license: MIT
---

# Session Start

Run this once before the first code edit of a task. It is a read-only grounding pass, not permission to change branches, pull, or deploy.

## Tight loop

1. Locate the repository root and read its root agent instructions plus task-relevant rules, skills, workflow files, hook configuration, and hook scripts.
2. Inspect workspace state:

   ```bash
   git rev-parse --show-toplevel
   git status --short --branch
   git worktree list
   git branch --show-current
   ```

3. Fetch the relevant remote ref if network access is available, then report ahead/behind state. Never auto-pull, reset, or fast-forward a user worktree.

   ```bash
   git fetch origin <relevant-base-branch>
   git rev-list --left-right --count <relevant-base-branch>...origin/<relevant-base-branch>
   ```

4. Restate the requested outcome in one sentence and name the exact scope: affected user surface, project/workspace level, API/RPC/table, or deployment environment.
5. Before asserting something is absent or designing a replacement, search the canonical implementation and history for existing components, hooks, RPCs, migrations, tests, and adjacent worktrees/PRs. Report the paths searched and the reusable seams found.
6. For a change that may overlap parallel work, inspect open PRs and worktrees read-only. Flag concrete file overlap or say that none was found.

## Completion report

Report only the evidence needed to begin safely:

- repository root, branch, worktree status, and freshness;
- instructions/config/hooks loaded;
- one-sentence scope interpretation;
- existing seams and active overlap;
- the specific rules/skills that govern the next action.

If the branch is stale, detached, protected, or the task scope remains materially ambiguous, stop before editing and explain the blocker. Do not turn a read-only preflight into a cleanup or deployment operation.
