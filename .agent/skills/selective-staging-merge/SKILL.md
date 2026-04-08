---
name: selective-staging-merge
description: Merges a staging branch into main while excluding specific tickets that haven't passed QA. Handles QA-fix ticket detection (which implies parent feature exclusion), already-in-main deduplication, dry-run conflict checking with proper cleanup, and safe execution via temp branch. Works across all three repos (vettedai-audition, vetted-congrats, backend-restructing).
version: 1.1.0
license: MIT
---

# Selective Staging Merge

Merge a staging branch → `main` while holding back specific tickets that haven't passed QA yet.

Works across all three repos — staging branch name is auto-detected per repo.

**Announce at start:** "I'm using the selective-staging-merge skill."

## When to Use

- After a QA cycle where some tickets passed and others didn't
- When the user says "merge staging to main but skip tickets #NNN"
- Periodically to ship what's ready without blocking on slower tickets

## Invocation

```
/selective-staging-merge                              # Interactive — prompts for excluded tickets
/selective-staging-merge --exclude 412,413,506,405   # Tickets to hold back
```

---

## Workflow

### Phase 1: Gather Inputs

**Auto-detect staging branch** — check which known staging branch exists in this repo:

```bash
TARGET_BRANCH="main"

# Known staging branch names per repo (check in priority order)
STAGING_BRANCH=""
for candidate in lovable-staging verify-deployments backend-verify-deployment; do
  if git show-ref --verify --quiet refs/remotes/origin/$candidate 2>/dev/null; then
    STAGING_BRANCH=$candidate
    break
  fi
done

if [ -z "$STAGING_BRANCH" ]; then
  echo "No staging branch detected. Which branch should be merged into main?"
  # Ask the user
fi

echo "Staging branch: $STAGING_BRANCH"
```

| Repo | Staging Branch |
|------|---------------|
| `vettedai-audition-supabase-version` | `lovable-staging` |
| `vetted-congrats-Flow-GENEROUS` | `verify-deployments` |
| `backend-restructing` | `backend-verify-deployment` |

If excluded tickets not provided, ask:
> "Which ticket numbers should be held back? (comma-separated)"

Ensure local branches are current:
```bash
git fetch origin
git checkout $TARGET_BRANCH && git pull origin $TARGET_BRANCH
git checkout $STAGING_BRANCH && git pull origin $STAGING_BRANCH
git checkout $TARGET_BRANCH
```

---

### Phase 2: Fetch Ticket Context from Fizzy

For each excluded ticket, fetch title + column to determine ticket **type**.

```bash
source .env.local
for TICKET in $(echo $EXCLUDED_TICKETS | tr ',' ' '); do
  curl -s "https://app.fizzy.do/6102589/cards/$TICKET.json" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN" \
    -H "User-Agent: VettedAI/1.0" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"#{d['number']} | column={d.get('column',{}).get('name','')} | {d['title']}\")"
done
```

**QA-fix ticket detection.** A ticket is a QA-fix ticket if:
- Title contains: "QA fail", "fix QA", "address QA", "QA fixes"
- Column is: "QA Failed", "QA to be confirmed"
- Or the commit message says: "fix: address QA failures for..."

**⚠️ If QA-fix tickets are detected, warn the user:**

> "Ticket(s) #NNN are QA-fail tickets — they are fixes for a feature with **known failures**.
> Shipping the base feature without these fixes is worse than not shipping it at all.
> Recommend excluding the full parent feature. Shall I auto-detect and exclude the parent feature commits?"

If user confirms → proceed to **Phase 2b**. If not → proceed with only the explicitly referenced commits excluded (user accepts the risk).

---

### Phase 2b: Extended Exclusion — Auto-Detect Parent Feature

Find all commits touching the same files as the QA-fix commits.

```bash
# Get files touched by QA-fix commits
QA_FIX_FILES=$(for HASH in $QA_FIX_HASHES; do
  git show $HASH --name-only --format="" | grep -v "^$"
done | sort -u | tr '\n' ' ')

# Find all commits in staging ^main that touch those files
echo "Commits that touch the same files:"
git log --oneline $STAGING_BRANCH ^$TARGET_BRANCH -- $QA_FIX_FILES
```

Group commits by feature/PR by looking at nearby merge commits:
```bash
git log --oneline --merges $STAGING_BRANCH ^$TARGET_BRANCH | head -20
```

**Show the extended exclusion list to the user and ask for confirmation before adding them.**

The extended exclusion list will typically be: the QA-fix commits + all commits from the parent feature PR(s).

---

### Phase 3: Map Commits → Tickets

Get all commits in staging not yet in target:

```bash
git log --oneline $STAGING_BRANCH ^$TARGET_BRANCH
```

For each excluded ticket, find matching commits by:
1. **Direct message reference**: `grep "#$TICKET"` in commit messages
2. **Branch name in merge commit**: `grep -i "ticket-$TICKET\|/$TICKET-\|-$TICKET/"` in merge commit messages
3. **Manually confirmed** (Phase 2b output)

Build two sets:
- `EXCLUDED_HASHES` — all commits to skip
- `CANDIDATE_HASHES` — all remaining commits (oldest first)

```bash
# All commits in staging not in main, oldest first
ALL_COMMITS=$(git log --reverse --format="%H" $STAGING_BRANCH ^$TARGET_BRANCH)

EXCLUDED_HASHES=(...)   # from ticket mapping + Phase 2b
CANDIDATE_HASHES=()
for HASH in $ALL_COMMITS; do
  if [[ ! " ${EXCLUDED_HASHES[@]} " =~ " $HASH " ]]; then
    CANDIDATE_HASHES+=($HASH)
  fi
done
```

---

### Phase 4: Already-In-Main Check

**This step is critical.** Hotfixes are often cherry-picked directly to main on a fast track. Without this check you'll attempt to re-apply changes already there and get conflicts.

```bash
TRULY_NEW=()
ALREADY_IN_MAIN=()

for HASH in "${CANDIDATE_HASHES[@]}"; do
  # Check 1: exact commit ancestry
  if git merge-base --is-ancestor $HASH $TARGET_BRANCH 2>/dev/null; then
    ALREADY_IN_MAIN+=($HASH)
    continue
  fi

  # Check 2: same commit message already in main (hotfix re-applied with new hash)
  SHORT_MSG=$(git log --format="%s" -1 $HASH | cut -c1-60)
  if git log --oneline $TARGET_BRANCH | grep -qF "$SHORT_MSG"; then
    ALREADY_IN_MAIN+=($HASH)
    continue
  fi

  TRULY_NEW+=($HASH)
done

echo "Already in main: ${#ALREADY_IN_MAIN[@]} commits (skipping)"
echo "To cherry-pick:  ${#TRULY_NEW[@]} commits"
```

---

### Phase 5: Dry-Run

⚠️ **Critical:** `git cherry-pick --no-commit` stages changes but doesn't commit them. The staged state **will block the real run** if not cleaned up properly. Follow the cleanup procedure exactly.

```bash
# Snapshot untracked files BEFORE dry-run (to identify new files created by it)
git ls-files --others --exclude-standard | sort > /tmp/pre_dryrun_untracked.txt

# Create temp branch for dry-run (NEVER test directly on main)
git checkout -b dry-run-staging-merge

# Abort any stale cherry-pick state from a previous run
git cherry-pick --abort 2>/dev/null; true

# Dry-run — stages all changes without committing
git cherry-pick --no-commit "${TRULY_NEW[@]}"
DRY_RUN_EXIT=$?

# Check result
if [ $DRY_RUN_EXIT -eq 0 ]; then
  echo "✅ Dry-run: zero conflicts"
  CONFLICT_FILES=""
else
  CONFLICT_FILES=$(git diff --name-only --diff-filter=U)
  echo "❌ Conflicts in: $CONFLICT_FILES"
fi

# ── MANDATORY CLEANUP ────────────────────────────────────────────────────────
# The dry-run leaves staged changes. ALL of these must be cleared or the real
# cherry-pick will fail with "your local changes would be overwritten".

# Step 1: abort any in-progress cherry-pick
git cherry-pick --abort 2>/dev/null; true

# Step 2: unstage all staged changes
git reset HEAD 2>/dev/null; true

# Step 3: restore all modified tracked files
git restore . 2>/dev/null; true

# Step 4: remove NEW untracked files created by the dry-run
# (compare against pre-dryrun snapshot — preserve pre-existing untracked dirs)
git ls-files --others --exclude-standard | sort > /tmp/post_dryrun_untracked.txt
comm -13 /tmp/pre_dryrun_untracked.txt /tmp/post_dryrun_untracked.txt | while read f; do
  rm -f "$f"
  # remove parent dir if now empty
  rmdir "$(dirname $f)" 2>/dev/null; true
done

# Step 5: tear down the temp branch
git checkout $TARGET_BRANCH
git branch -D dry-run-staging-merge 2>/dev/null; true

# Verify clean
echo "Working tree status after cleanup:"
git status --short
# ─────────────────────────────────────────────────────────────────────────────
```

**If conflicts detected** — check whether HEAD already has the conflicting change:
```bash
# Common pattern: hotfix was cherry-picked to main; it shows as conflict because
# the patch context differs but the end-state is already there.
git show HEAD:$CONFLICT_FILE | grep -c "$CONFLICTING_LINE" && echo "Change already in main — skip this commit"
```

If the conflicting change is already in main → move that commit to `ALREADY_IN_MAIN` and re-run the dry-run without it.

If it's a genuine conflict → pause, show the user, and ask how to handle before proceeding.

---

### Phase 6: Confirm With User

Show the full plan and ask for **explicit confirmation** before touching main. This will push to production.

```
Selective Staging Merge — Ready to Execute
═══════════════════════════════════════════
Merging: lovable-staging → main

✅ Cherry-picking (N commits, oldest → newest):
  a1b2c3d  fix: PostHog login_success timing fix (#393)
  d4e5f6g  perf: rejection feedback inline processing
  ...

⏸️  Held back (N commits — pending QA):
  Finalists v2 base feature (#411, #415):
    94f87eb  finalists-v2-nav-pill-strip-411
    7fc7ed9  feat: Implement Finalists v2 detail panel
    ...
  QA fixes — not yet re-verified (#412, #413):
    fc8d931  fix: address QA failures for Finalists v2
    1a24a35  fix: apply QA fixes for ThumbsDecision

ℹ️  Already in main (N commits — skipped):
  ea45ee9  fix: prevent premature aggregation (hotfixed)
  785b1c1  fix: exclude rejected candidates (hotfixed)

Dry-run: ✅ Zero conflicts

⚠️  This will push to origin/main and trigger a Vercel production deploy.
Proceed? [Y/n]
```

---

### Phase 7: Execute

```bash
MONTH_LABEL=$(date +%b%Y | tr '[:upper:]' '[:lower:]')

# Fresh pull — guard against changes since Phase 1
git checkout $TARGET_BRANCH && git pull origin $TARGET_BRANCH
git checkout -b partial-staging-merge-$MONTH_LABEL

# Cherry-pick for real
git cherry-pick "${TRULY_NEW[@]}"

# Verify
echo "Commits added:"
git log --oneline $TARGET_BRANCH..HEAD

# Build held-back summary for merge commit
HELD_BACK_LIST=$(for H in "${EXCLUDED_HASHES[@]}"; do
  git log --oneline -1 $H 2>/dev/null
done | head -20)

# Merge to target with descriptive message
git checkout $TARGET_BRANCH
git merge partial-staging-merge-$MONTH_LABEL --no-ff -m \
  "merge: $STAGING_BRANCH → $TARGET_BRANCH (partial, $(date +'%b %Y'))

Includes: $(git log --oneline ${TRULY_NEW[@]} | cut -c9- | paste -sd '; ' - | cut -c1-200)

Held back (pending QA):
$HELD_BACK_LIST"

# Push
git push origin $TARGET_BRANCH

# Cleanup
git branch -d partial-staging-merge-$MONTH_LABEL
```

---

### Phase 8: Post-Merge Report

```
Merge Complete ✅
═════════════════
- N commits merged to main
- Vercel deploy triggered
- N commits held back in lovable-staging

⚠️  Migrations to apply manually via Supabase Dashboard SQL editor:
  [list any supabase/migrations/*.sql files in the cherry-picked commits]
  Apply in filename order (timestamps are ordered).

When held-back tickets pass QA:
  git checkout main && git pull origin main
  git merge lovable-staging
  (git will only apply the N commits not yet in main — no re-merging of what's already there)
```

---

## Edge Cases

### Merge commits in the excluded range

Merge commits (`Merge pull request #N from .../branch`) can't be cherry-picked directly. They are effectively skipped — their constituent commits are already in the individual commit list. If a merge commit from an INCLUDED PR needs to land, cherry-pick with `-m 1`:
```bash
git cherry-pick -m 1 <merge-commit-hash>
```

### Stale cherry-pick state

If you see `error: cherry-pick is already in progress`:
```bash
git cherry-pick --abort
# Then re-run from Phase 5
```

### No new commits after deduplication

If `TRULY_NEW` is empty after the already-in-main check, all staging changes are already in main. Report this and stop — no merge needed.

### When held-back tickets eventually clear QA

```bash
git checkout main && git pull origin main
git merge lovable-staging
# Only the N held-back commits apply — the partial merge creates a clean shared ancestry
```

---

## Key Learnings (from first run, Apr 2026)

| # | Learning | Why It Matters |
|---|----------|----------------|
| 1 | **QA-fix ticket = exclude the parent feature too** | Shipping the base feature without its QA fixes is worse than not shipping it. The broken state is known-broken. |
| 2 | **Always check "already in main" before building the list** | Hotfixes get cherry-picked to main on a fast track. 10 of 17 apparent candidates were already there — without this check, guaranteed conflicts. |
| 3 | **`--no-commit` dry-run leaves staged changes that block the real run** | `git cherry-pick --abort` alone is not enough. Must also `git reset HEAD` + `git restore .` + `rm` new untracked files. |
| 4 | **Snapshot untracked files BEFORE dry-run** | Lets you identify exactly which new files the dry-run created, so you can remove only those without touching pre-existing untracked dirs (`.claude/tickets/`, `reports/`). |
| 5 | **Use a temp branch, never cherry-pick directly to main** | Conflicts surface safely on the temp branch. Main stays clean until you explicitly merge. |
| 6 | **Conflict where HEAD already has the change = hotfix already applied** | See it in dry-run output: HEAD section has the change, cherry-pick section is empty. Remove that commit from `TRULY_NEW`. |
| 7 | **Merge commit message should list held-back hashes explicitly** | When the held-back tickets clear QA, the merge commit tells you exactly what's pending without having to re-derive it. |
| 8 | **Never `git stash --include-untracked`** | Stashes skill directories (`.agent/skills/`, `.claude/tickets/`) making skills unavailable until popped. Use plain `git stash` or `git checkout` directly. |

---

## Fizzy API Reference

- **Token**: `source .env.local` → `$FIZZY_API_TOKEN`
- **Account slug**: `6102589`
- **Card details**: `GET /cards/{NUMBER}.json`
- Always append `.json` to action endpoints — returns 422 without it

## Branch Reference

| Branch | Purpose |
|--------|---------|
| `lovable-staging` | Integration branch — all PRs merge here first |
| `main` | Production branch — what Vercel deploys |
| `qa-mirror` | QA testing branch — mirrors lovable-staging post-fixes |
