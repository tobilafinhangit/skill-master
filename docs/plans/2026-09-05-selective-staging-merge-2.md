# Selective Staging Merge 2.0 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare a reproducible, fail-closed selective release candidate from pinned integration and production revisions without mutating the caller worktree or publishing it.

**Architecture:** Keep operator workflow and evidence policy in the selective-staging-merge skill. Put deterministic Git inventory, manifest validation, isolated replay, verification, and owned-resource cleanup in a Python standard-library helper. The helper records all inputs, decisions, provenance, and blocked states in a versioned JSON manifest.

**Tech Stack:** Python 3 standard library, `unittest`, Git CLI, JSON manifests.

---

### Task 1: Manifest and inventory contracts

**Files:**
- Create: `.agent/skills/selective-staging-merge/tests/test_selective_release.py`
- Create: `.agent/skills/selective-staging-merge/scripts/selective_release.py`

**Steps:** Write failing tests for schema validation, exactly-one disposition, dependency blocking, SHA pin checks, deterministic path/commit ordering, merge-base discovery, ordinary commits, and merge units. Run the focused suite to confirm import/behavior failures. Implement the smallest pure validation and Git inventory functions, then rerun.

### Task 2: Mapping and deterministic replay

**Files:**
- Modify: `.agent/skills/selective-staging-merge/tests/test_selective_release.py`
- Modify: `.agent/skills/selective-staging-merge/scripts/selective_release.py`

**Steps:** Add real temporary-repository tests for merge-only resolution, constituent listing, mixed/unknown dependencies, rename paths, revert/supersession evidence, and replaying a merge once with mainline 1. Implement checked argument-array Git operations and stop on conflicts or unexpected empty cherry-picks.

### Task 3: Isolation, recovery, and cleanup

**Files:**
- Modify: `.agent/skills/selective-staging-merge/tests/test_selective_release.py`
- Modify: `.agent/skills/selective-staging-merge/scripts/selective_release.py`

**Steps:** Test dirty/staged/untracked/ignored caller state, cherry-pick state, occupied worktree/branch names, unusual filenames, failed creation, successful-prefix failure, and refused foreign/dirty cleanup. Implement owned worktree metadata, unique branch/path allocation, failure recording, and exact cleanup guards.

### Task 4: Verification and publication boundary

**Files:**
- Modify: `.agent/skills/selective-staging-merge/tests/test_selective_release.py`
- Modify: `.agent/skills/selective-staging-merge/scripts/selective_release.py`

**Steps:** Add fake-adapter tests for stale source/base revisions, candidate drift, migration/runtime blockers, rejected/ambiguous publication responses, and read-only command guards. Implement `verify` as a pre-publication gate that refreshes exact refs and checks candidate identity/tree/evidence without push, merge, deploy, or database mutation.

### Task 5: Skill rewrite and merge-to-prod handoff

**Files:**
- Modify: `.agent/skills/selective-staging-merge/SKILL.md`
- Modify: `.agent/skills/merge-to-prod/SKILL.md`

**Steps:** Replace the old cherry-pick/main-push instructions with the 2.0 workflow, helper commands, readiness gates, blocked cases, recovery rules, and explicit authorization boundary. Update merge-to-prod only to hand excluded staging work to this workflow. Run selective, merge-to-prod, and repository suites; inspect the final diff and document intentional blocks/limitations.
