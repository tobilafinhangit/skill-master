---
name: hotfix
description: Codifies the P0 hotfix flow — base off main (skipping QA), open a PR to main, then cherry-pick the merge commit back to the integration branch so staging doesn't drift. Confirms P0 status before going main-route. Use when there's a live production incident that cannot wait for the standard staging→QA→main pipeline.
version: 1.0.0
license: MIT
---

# Hotfix

Ship a fix to production without going through the integration branch. Always cherry-pick back to staging afterward so the integration branch stays a superset of main.

**Announce at start:** "I'm using the hotfix skill."

## When to Use

- Live production incident: paying users blocked, data loss in progress, security exposure
- A staging-side bug that would normally take a QA cycle but the cost of waiting exceeds the cost of skipping QA
- User says: "this is a hotfix", "P0", "production is broken", "we need to skip QA on this"

**Do NOT use for:**
- Features, even urgent ones — those go through staging
- Cleanup, refactoring, copy changes, UI polish — staging
- Anything where QA would catch a class of problem you haven't ruled out — staging

If unsure whether something is hotfix-worthy, ask. Default to staging.

## Invocation

```
/hotfix                        # confirms P0, prompts for slug + description
/hotfix <slug>                 # uses provided slug, still confirms P0
/hotfix <slug> --skip-confirm  # only when user has already explicitly said "this is a hotfix"
```

---

## Phase 1: Confirm P0

Before cutting any branch, the skill must confirm this is genuinely a hotfix. The deployment shape (skip QA, separate cherry-pick PR) doubles the work of a normal feature — only worth it if the production incident makes the wait cost higher.

Ask the user once, plainly:
> "Confirming this is a P0 hotfix — production is broken or there's a live user-impacting incident, and we need to ship to `main` directly without going through staging QA. Is that right? (If unsure, we should base off `lovable-staging` instead.)"

If the user wavers, suggest the standard flow (`branch-and-worktree-policy.md` default) and stop.

If the user provided `--skip-confirm` and a previous message in this chat already established it's a hotfix, skip the prompt.

---

## Phase 2: Auto-Detect Per Repo

| Item | How it's detected |
|------|-------------------|
| **Target branch** (`main`) | `git symbolic-ref refs/remotes/origin/HEAD` → else `main` → else `master` |
| **Integration branch** (`lovable-staging`) | 1) Read `.claude/rules/working-branch.md` for explicit name; 2) else first of `lovable-staging` / `verify-deployments` / `backend-verify-deployment` existing on `origin` |
| **Fizzy ticket #** | Optional. If the user provides one, use it for branch naming. Otherwise use a slug. |

```bash
git fetch origin --quiet
TARGET=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|^refs/remotes/origin/||' || echo "main")
# Determine integration branch:
INTEGRATION=$(grep -E '^\`[a-z-]+\`' .claude/rules/working-branch.md 2>/dev/null | head -1 | tr -d '`' | awk '{print $1}')
INTEGRATION=${INTEGRATION:-lovable-staging}
```

---

## Phase 3: Cut Worktree off `main`

Per `branch-and-worktree-policy.md`, the `-main` suffix on the branch name is the load-bearing signal that this PR targets `main` directly. Match it.

```bash
SLUG="<short-slug>"           # from user or derived from description
WORKTREE_DIR=".claude/worktrees/hotfix-${SLUG}"
BRANCH="hotfix/${SLUG}-main"

git worktree add -b "$BRANCH" "$WORKTREE_DIR" "origin/${TARGET}"
cd "$WORKTREE_DIR"
```

Confirm with the user once:
> "Cut a worktree at `.claude/worktrees/hotfix-<slug>` off `origin/<main>` as `hotfix/<slug>-main` — sound right?"

After confirmation, proceed in this worktree for the rest of the chat.

---

## Phase 4: Apply Fix + Open PR to `main`

Standard implementation flow. Then:

```bash
git push -u origin "$BRANCH"

gh pr create --base "$TARGET" --head "$BRANCH" \
  --title "🔥 hotfix: <description> [skip QA]" \
  --body "$(cat <<EOF
## Why this skips QA
<one-paragraph: production incident, user impact, why waiting for staging QA is more expensive than the risk of skipping it>

## Fix
<terse: what changed, why, and the smallest blast radius reasoning>

## Verification
- [ ] Manual smoke test on production after merge: <specific check>
- [ ] Cherry-pick PR to <integration> opened (filed automatically by /hotfix after this merges)

## Cherry-pick plan
After this PR merges to \`$TARGET\`, run \`/hotfix --finalize <PR#>\` to open the cherry-pick PR back to \`$INTEGRATION\`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

The `🔥` + `[skip QA]` markers are explicit signals to anyone reviewing the PR list that this branch deliberately bypassed the standard flow.

---

## Phase 5: After Merge — Cherry-Pick to Integration

`main` and `<integration>` must not diverge. The hotfix lives on `main`; the integration branch needs the same commit so future staging→main PRs don't try to revert it.

When the user invokes `/hotfix --finalize <PR#>` (or simply says "the hotfix merged, cherry-pick it"):

```bash
# Identify the merge commit
MERGE_SHA=$(gh pr view <PR#> --json mergeCommit --jq '.mergeCommit.oid')

# Cut a separate worktree off the integration branch
git fetch origin --quiet
git worktree add -b "hotfix/${SLUG}-cherrypick" \
  ".claude/worktrees/hotfix-${SLUG}-cherrypick" "origin/${INTEGRATION}"
cd ".claude/worktrees/hotfix-${SLUG}-cherrypick"

# Cherry-pick. If conflicts arise, the integration branch has diverged
# in a way that interacts with the hotfix — pause and ask the user.
git cherry-pick "$MERGE_SHA" -m 1   # -m 1 if it's a merge commit, otherwise drop -m
git push -u origin "hotfix/${SLUG}-cherrypick"

gh pr create --base "$INTEGRATION" --head "hotfix/${SLUG}-cherrypick" \
  --title "chore: cherry-pick hotfix <slug> into ${INTEGRATION}" \
  --body "Cherry-picks #<PR#> (merged to \`main\`) back into \`${INTEGRATION}\` so the integration branch stays a superset of \`main\`. No new changes."
```

The cherry-pick PR can be merged with admin bypass — there's nothing new to QA, and not landing it leaves staging diverged.

---

## Phase 6: Verify

Both deploys must be green:
- `main` deploy reflects the fix in production (Vercel deploy logs / live smoke test)
- `<integration>` deploy reflects the fix in staging
- `git log origin/main..origin/<integration>` and `git log origin/<integration>..origin/main` both show the fix only on the side(s) that should — usually empty in both directions for a single hotfix that's been cherry-picked

---

## What NOT to do

- ❌ Don't base a hotfix off `lovable-staging` then "promote it" later — that's just a feature branch wearing a hotfix hat, and you've still gone through staging.
- ❌ Don't merge `<integration>` into `main` instead of doing the cherry-pick — that would drag everything else on staging into prod.
- ❌ Don't skip the cherry-pick step. The integration branch will quietly diverge from main and the next staging→main PR will look weird.
- ❌ Don't reuse the hotfix branch for follow-ups. New work = new branch off whichever base is correct for that work.
- ❌ Don't run `git stash --include-untracked` to switch out of the worktree — it sweeps untracked skill directories. Plain `git stash` or just `cd` away.

---

## Related Rules

- `.claude/rules/branch-and-worktree-policy.md` — defines hotfix flow + branch naming
- `.claude/rules/working-branch.md` — integration branch identity (lovable-staging, qa-mirror)
- `.claude/rules/no-stash-include-untracked.md` — worktree-adjacent hazard
- Skill `merge-to-prod` — counterpart for the standard staging→main batched flow
