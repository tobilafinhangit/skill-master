---
name: qa-handoff
description: Hands off completed work to QA by posting a testing guide on the Fizzy card, moving it to the QA column, assigning Elvis, and syncing qa-mirror. Auto-detects per-repo conventions (integration branch, qa-mirror presence, Supabase migrations). Use after pushing fixes when work is ready for QA testing.
version: 2.0.0
license: MIT
---

# QA Handoff

After pushing code, hand it off to QA in one step — post a testing guide, move the card, assign the tester, sync qa-mirror.

**Announce at start:** "I'm using the qa-handoff skill to hand this off to QA."

## When to Use

- After committing and pushing a fix or feature to the repo's integration branch
- After a PR verification + fix cycle
- When the user says "hand this to QA", "move to QA", "ready for testing"

## Required Input

Ask the user if not provided:
- **Fizzy card number** (e.g., `315`)
- **PR number** — or detect from recent `gh pr view`
- **Branch name** — or detect from `git branch --show-current`

Supports `--dry-run` flag: print all planned actions (Fizzy payloads, git commands, branch ops) without executing. Useful on a new repo before a real handoff.

## How the Skill Adapts Per Repo (No Config Required)

The skill auto-detects everything it needs. Run it in any repo — it just works.

| What it detects | How |
|---|---|
| **Integration branch** (e.g. `lovable-staging`, `verify-deployments`, `main`) | 1) Read `.claude/rules/working-branch.md` or `.claude/rules/integration-branch.md` if either exists; 2) else use first of `lovable-staging` / `verify-deployments` / `main` that exists on `origin` |
| **qa-mirror branch** | Check `origin/qa-mirror`. If missing, skip the qa-mirror sync step entirely |
| **Supabase migrations handling** | Check if `supabase/migrations/` exists |
| **Fizzy board + QA column** | Derived from `card.board.id` returned in Step 1 (see Board Reference at the bottom) |

The pre-flight push check (Step 2) always runs — it's cheap and catches a real failure mode.

### Optional override: `.claude/skills/qa-handoff.json`

Only needed if auto-detection picks the wrong value. Any field can be overridden:

```json
{
  "integrationBranch": "lovable-staging",
  "qaMirrorBranch": "qa-mirror",
  "hasSupabaseMigrations": true
}
```

If the file is missing, the skill uses auto-detected values. Don't create one unless you need it.

## Workflow

### Step 1: Gather Context

```bash
BRANCH=$(git branch --show-current)
LAST_COMMIT=$(git log --oneline -1)
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null

CARD_JSON=$(curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN")
```

Extract from card JSON: `board.id`, `column.name`, `assignees[].id`.

Use `board.id` to look up the right QA column ID from the Board Reference at the bottom of this file.

### Step 2: Pre-Flight Push Check

Verify all local work is on the remote branch. QA pulls from `origin/` — local-only commits fail the card.

```bash
# 1. Unpushed commits
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/$BRANCH 2>/dev/null)
if [ "$LOCAL" != "$REMOTE" ]; then
  echo "⚠️  Local HEAD ahead of origin/$BRANCH"
  git log --oneline origin/$BRANCH..HEAD
fi

# 2. Untracked migration files (if hasSupabaseMigrations)
UNTRACKED=$(git ls-files --others --exclude-standard supabase/migrations/)
[ -n "$UNTRACKED" ] && echo "⚠️  Untracked migrations: $UNTRACKED"

# 3. Uncommitted changes
git status --short
```

**On finding issues:** stop, alert the user, don't proceed. Cards #430 and #431 historically failed QA because commits existed locally but weren't pushed before Elvis pulled the branch.

### Step 3: Migration Scan (only if `hasSupabaseMigrations`)

```bash
gh pr diff {NUMBER} --name-only | grep "supabase/migrations/"
```

If migrations are present:
- **QA comment** gets a "⚠️ Migration — Verify Before Testing" block with a **verification SELECT only** (not DDL — Elvis confirms migrations ran, he doesn't run schema changes)
- **PR description** gets raw DDL in a "⚠️ Migration — Run on Production After Merge" block (so Tobi has it visible at merge time)

**Role separation is critical:**
- Elvis (QA): runs the verification SELECT to confirm the migration was applied to staging before testing
- Tobi (Owner): runs the raw DDL against production after QA passes and PR merges to main

### Step 4: Update PR Description if Migrations Present

If the PR has migrations and the body doesn't already contain a migration block, append:

```bash
BODY=$(gh pr view {NUMBER} --json body -q .body)
gh pr edit {NUMBER} --body "$BODY

---
## ⚠️ Migration — Run on Production After Merge

\`\`\`sql
-- Paste the migration SQL here (from the migration file in the diff)
\`\`\`

**Staging:** Run before QA testing begins.
**Production:** Run manually via Supabase SQL editor after this PR merges to main.
Do NOT use \`supabase db push\` — migration files may have been edited after first apply."
```

### Step 5: Build QA Comment

Post an HTML comment to the Fizzy card. Must include:

1. **Summary table** — one row per change (what, why)
2. **Migration check** — verification SELECT block (only if migrations present)
3. **Code verification** — CLI commands (tsc, lint)
4. **UI testing steps** — step-by-step per change, specific viewports/flows
5. **Regression checks** — checklist of related flows that must not break
6. **What was NOT changed** — guardrails / files explicitly untouched

**Migration verification block (when applicable):**

```html
<h3>⚠️ Migration — Verify Before Testing</h3>
<p>Run this SELECT in the <strong>staging</strong> Supabase SQL editor to confirm the migration was applied. If it returns 0 rows, ping Tobi.</p>
<pre>SELECT column_name FROM information_schema.columns
WHERE table_name = '{table}' AND column_name = '{column}';</pre>
<p><strong>Do not run DDL here</strong> — schema changes are Tobi's responsibility at merge time.</p>
```

**Formatting rules:**
- HTML only (Fizzy renders HTML, not Markdown)
- Tables: `<table><tr><th>...</th></tr></table>`
- Lists: `<ol>` / `<ul>`
- Code: `<code>` inline, `<pre>` blocks
- Checkboxes: `☐` character (Fizzy doesn't support `<input>`)

```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": {"body": "<h2>QA Testing Guide — PR #...</h2>..."}}'
# 201 = success
```

### Step 6: Move Card to QA Column

Using the QA column ID derived from `card.board.id` in Step 1:

```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/triage.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"column_id\": \"$QA_COLUMN_ID\"}"
# 204 = success
```

If already in QA column, skip and note it.

### Step 7: Assign Elvis (QA Lead)

Elvis's user ID: `03fcio1h8spstjpkc82vciugk`

**Critical:** Check `assignees` from Step 1 first. The endpoint TOGGLES — calling it when Elvis is already assigned will UNASSIGN him.

```bash
if ! echo "$ASSIGNEES" | grep -q "03fcio1h8spstjpkc82vciugk"; then
  curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/assignments.json" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"assignee_id": "03fcio1h8spstjpkc82vciugk"}'
fi
```

### Step 8: Sync qa-mirror (skip if `qaMirrorBranch` not detected)

`qa-mirror` points at the live production DB and must reflect the integration branch. Sync after every handoff:

```bash
git fetch origin $INTEGRATION_BRANCH $QA_MIRROR_BRANCH
git checkout $QA_MIRROR_BRANCH
git merge origin/$INTEGRATION_BRANCH --no-ff \
  -m "Merge remote-tracking branch 'origin/$INTEGRATION_BRANCH' into $QA_MIRROR_BRANCH"
git push origin $QA_MIRROR_BRANCH
git checkout $INTEGRATION_BRANCH
git pull --ff-only   # fast-forward local integration branch (was stale before fetch)
```

If merge conflicts: resolve (prefer integration branch) before pushing.
If `qa-mirror` is already up to date: skip and note it.

**Why the final pull:** the merge above uses `origin/$INTEGRATION_BRANCH`, which updates qa-mirror but never advances local integration branch. Without `git pull --ff-only`, every handoff leaves you on a stale integration branch — the next task would branch off that stale base.

### Step 9: Confirm Handoff

```
QA Handoff Complete:
- ✅ QA comment posted on Fizzy #{NUMBER}
- ✅ Card moved to "{QA_COLUMN_NAME}" column
- ✅ Elvis Muchiri assigned (or: already assigned — skipped)
- ✅ qa-mirror synced with {INTEGRATION_BRANCH} (or: already up to date / no qa-mirror in this repo)
- 🔗 PR: {PR_URL}
```

## Fizzy API Reminders

- Always use `.json` suffix on all endpoints (returns 401 without it)
- Token: `source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null` → `$FIZZY_API_TOKEN`
- Account slug: `6102589`
- Assignments TOGGLE — always check current state first
- Card creation returns URL in `Location` header, not response body

## Team Reference

| Person | Role | User ID |
|--------|------|---------|
| Elvis Muchiri | QA Lead | `03fcio1h8spstjpkc82vciugk` |
| Daniella Mutai | Engineer | `03fma4gpioiosyf3g9w409r8t` |
| Tobi Lafinhan | Owner | `03f58r3y17c4p4ucpvaf7mn5g` |

## Board Reference

Used by Step 1 to derive the QA column from `card.board.id`:

| Board | Board ID | QA Column Name | QA Column ID |
|-------|----------|---------------|--------------|
| Bugs | `03fl735hqcd0h1pettl8o94oo` | QA To be Confirmed | `03fnl3h1becpuazzhahxbn208` |
| Congrats | `03f58rc5c48jorujpxqp5da5b` | QA to confirm fixed | `03f58rxrkofln7o86yce47gvk` |
| Vetted | `03faozjl3gdngcoyzpkr4vf87` | QA to be confirmed | `03fdi5xotshcmiuqk8pj24b23` |

When a new board is added to the ecosystem, add a row here.
