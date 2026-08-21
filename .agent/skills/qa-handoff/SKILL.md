---
name: qa-handoff
description: Hands off completed work to QA by merging the PR into the integration branch, posting a testing guide on the Fizzy card, moving it to the QA column, assigning Elvis, and syncing qa-mirror. Detects a re-handoff (a card QA previously failed) and requires a point-by-point "what changed since your fail" reply. Auto-detects per-repo conventions (integration branch, qa-mirror presence, Supabase migrations). Use after a PR is approved (or pushed direct) and ready for QA testing, or after fixing a QA-failed card.
version: 2.3.1
license: MIT
---

# QA Handoff

After a PR is approved (or a direct push to integration is done), hand it off to QA in one step — merge the PR, post a testing guide, move the card, assign the tester, sync qa-mirror.

**Announce at start:** "I'm using the qa-handoff skill to hand this off to QA."

## When to Use

- After a PR is approved and ready for QA (skill will merge it)
- After committing and pushing directly to the repo's integration branch (skill will skip the merge step)
- After a PR verification + fix cycle
- **After fixing a card that QA previously failed** — this is a **re-handoff**, see Step 0 (the skill detects it and adds a required "what changed since your fail" reply)
- When the user says "hand this to QA", "move to QA", "ready for testing", "back to QA", "re-test this"

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
| **Supabase migrations handling** | Check if `supabase/migrations/` exists at repo root OR one level deep (e.g. `congrats/supabase/migrations/`) |
| **Staging DB ref** (for auto-applying migrations to staging, Step 3.5) | From `qa-handoff.json` `stagingDbRef` if set; else **not auto-applied** — the skill falls back to prompting the user. Don't guess a ref. |
| **Fizzy board + QA column** | Derived from `card.board.id` returned in Step 1 (see Board Reference at the bottom) |

The pre-flight push check (Step 2) always runs — it's cheap and catches a real failure mode.

### Optional override: `.claude/skills/qa-handoff.json`

Only needed if auto-detection picks the wrong value. Any field can be overridden:

```json
{
  "integrationBranch": "lovable-staging",
  "qaMirrorBranch": "qa-mirror",
  "hasSupabaseMigrations": true,
  "stagingDbRef": "tobsmmjzmlljtyikujlr"
}
```

`stagingDbRef` is the Supabase project/branch ref whose database the staging preview points at. Set it so Step 3.5 can auto-apply the PR's migrations to the staging DB — the single biggest cause of "QA Failed for a non-code reason." If absent, Step 3.5 prompts the user instead of guessing. **Refs are per-repo — never hardcode one repo's ref for another.** Known refs:

| Repo | Staging ref | Prod ref |
|---|---|---|
| Vetted (`vettedai-audition-supabase-version`) | `tobsmmjzmlljtyikujlr` | `lagvszfwsruniuinxdjb` |
| Congrats (`vetted-congrats-Flow*`, `backend-restructing`) | `prpnmonpildkfajgrepb` (persistent `dev` branch of prod) | `uvszvjbzcvkgktrvavqe` |

If the file is missing, the skill uses auto-detected values. Don't create one unless you need it.

## Workflow

### Step 0: Re-Handoff Detection — Did QA Already Fail This Card?

**This closes the "silent bounce-back" hole that stalled 7 cards at once (Vetted, 2026-07-16).** Every gate in this skill (3.5, 8.5, 8.6) protects the *first* handoff. Nothing protected the **return trip**: a card QA-failed, the owner fixed it, moved it back to the QA column — and posted **no comment saying what changed**. From the tester's seat the column says "test me" while the last note in the thread is *their own unanswered failure report*. They can't tell "fixed, re-test" from "column moved, nothing done", so they stall and escalate. All 7 cards had real fixes already shipped; the only missing artifact was a reply. **A bounce-back without a reply is not a handoff.**

Run this **first**, before anything else. It's read-only and cheap.

```bash
# Does this card have a prior QA-fail in its history?
COMMENTS=$(curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0")

# OWNER = whoever is doing this handoff (you). Excluded so the detector can't
# match your OWN reply — a reply quoting "your 2026-07-14 FAIL" is an ANSWER to a
# fail, not a new one. Self-matching makes every card look permanently re-failed.
OWNER="Tobi Lafinhan"

echo "$COMMENTS" | OWNER="$OWNER" python3 -c "
import json,sys,re,os
owner=os.environ['OWNER']
cs=json.load(sys.stdin)
# TWO independent fail signals. The move is authoritative; the verdict text is a
# backstop for testers who report a fail without moving the card.
VERDICT = re.compile(r'status:\s*(❌|⛔|\bFAIL\b)|^\s*(❌|⛔)|\bstatus\b.{0,12}\bFAIL\b', re.I|re.M)
MOVED_FAIL = re.compile(r'moved this to .QA Failed.', re.I)
signal=None; findings=None
for c in cs:                      # chronological — last signal wins
    b=c.get('body') or {}
    txt=b.get('plain_text','') if isinstance(b,dict) else str(b)
    who=(c.get('creator') or {}).get('name','?')
    when=(c.get('created_at') or '')[:10]
    if who=='System':
        if MOVED_FAIL.search(txt): signal=('moved to QA Failed', when)
        continue
    if who==owner: continue       # never match your own reply
    if VERDICT.search(txt): signal=('explicit FAIL verdict', when)
    if signal: findings=(when, who, re.sub(r'\s+',' ',txt).strip())
if signal:
    print('RE-HANDOFF: prior QA-fail —', signal[1], 'via', signal[0])
    if findings:
        print('TESTER REPORT (' + findings[0] + ', ' + findings[1] + '):', findings[2][:600])
    else:
        print('NOTE: card was bounced but the tester left no written report — ask them what failed.')
else:
    print('FIRST HANDOFF: no unanswered QA-fail from a tester')
"
```

**Detector guardrails (each of these was a real false-positive/miss when this step was tested against live cards):**
- **Exclude your own comments.** A reply that says *"answering your 2026-07-14 FAIL"* contains the word FAIL. Match on it and the card looks re-failed forever.
- **A `System` "moved this to QA Failed" line IS a fail signal — and the authoritative one.** It carries no findings, so it can't be your *source* for what broke (use the tester's comment for that), but it is definitive proof the card was bounced. **Detecting on verdict text alone misses real bounce-backs** (verified 2026-07-16: 3 of 6 stalled cards missed — Elvis wrote `Status: ⏳ still not deploy-confirmed` and `Status: ⚠️ BLOCKED`, then moved all three to QA Failed anyway). Treat the move as the trigger; treat the text as the content.
- **A blocker in the *text* is not a fail — but a blocker that got *moved* is.** `Status: ⏳ BLOCKED on X` means "can't test yet"; if the tester left the card in the QA column it isn't a re-handoff (they're waiting on you, answer them and move on). If they moved it to QA Failed, it's a bounce regardless of how gently it's worded. **Trust the move over the wording** — testers' verdict vocabulary varies; the column move is unambiguous.
- **A bounce with no written report** is possible (move-line, no comment). Don't invent findings — ask the tester what failed.
- Detector says FIRST HANDOFF but you know QA bounced it? Trust the thread over the regex — read it and treat it as a re-handoff.

**If no prior fail → first handoff.** Continue to Step 1 normally; Step 0 is done.

**If a prior fail exists → this is a RE-HANDOFF.** Two things become mandatory:

1. **Read the tester's failure report in full and enumerate every distinct finding.** Not a skim — a list. Each finding gets an explicit disposition, and only three are valid:
   - **Fixed** — cite the *evidence*: commit SHA, PR number, deployed fn version + date, or a verifying query result. Never "should be fine now."
   - **Not a bug — the premise was wrong** — say *why* the expectation was mistaken, and correct the record. (Real example: a guide said "all 4 email templates must carry the FAQ token"; d3/d9 are a short nudge and a final-note closer — an FAQ block there is off-tone, so their lacking it was correct by design, not a partial migration. The tester's fail was sound *given the guide*; the guide was wrong.)
   - **Won't fix / out of scope** — say so plainly and why, so it isn't re-tested.
2. **The Step 5 QA comment MUST open with a "What changed since your fail" block** answering those findings point-by-point, before any test steps. This is the artifact whose absence caused the stall.

**Verify each "fixed" claim against ground truth before writing it** — the whole point is that the tester couldn't verify it themselves. Match the evidence to the failure class:

| Their fail was… | Prove the fix with |
|---|---|
| "label/copy still says X" | `git grep -n "<new string>" origin/$INTEGRATION_BRANCH -- <file>` → cite file + line |
| "migration/RPC not deployed" | Call the RPC with the new param. `PGRST202` = still old signature; **any other error (incl. an auth/permission error) = the param exists and arg-parsing passed** |
| "edge fn not deployed" | Management API `/v1/projects/<ref>/functions` → compare fn `updated_at` vs the PR merge time. Deploy-after-merge = live. **You cannot grep the deployed body** — Supabase ships edge fns as a compressed **ESZIP2** archive; source symbols don't survive. Say so rather than claiming a byte-match |
| "DB rows missing / cron hasn't run" | Run their exact query yourself and paste the real row count |
| "template/config content wrong" | Read the live row. **Confirm the column name first** — a typo'd column returns `42703` and a `select=*` "no match" reads exactly like "the feature is missing" |

**Guardrail — don't fix the tester's finding by moving the card.** If a finding is still real, the card does not go back to QA. Fix it first, or leave it in QA Failed with a note on what's outstanding. The QA column means *testable now*.

**Guardrail — stale guides.** If the implementation changed *after* the original testing guide was posted, the old guide is invalid and the tester's fail may be an artifact of it (they tested what you told them to test). Don't just answer the findings — **supersede the guide**: post a fresh one built from the *current* live state, and say explicitly that it replaces the earlier one.

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
- **Step 3.5 applies them to the staging DB** (below) so QA never fails for an un-applied migration
- **QA comment** gets a "✅ Migration — Applied to Staging" block with a **confirming SELECT** (should return rows)
- **PR description** gets raw DDL in a "⚠️ Migration — Run on Production After Merge" block (so Tobi has it visible at merge time)

**Role separation:**
- The skill (this step): applies the PR's migrations to the **staging DB** so the lovable-staging preview is testable
- Elvis (QA): runs the confirming SELECT (sanity check it landed) and tests
- Tobi (Owner): runs the raw DDL against **production** at the gated go-live (after QA passes)

### Step 3.5: Apply Migrations to the Staging DB (only if migrations present)

**This is the step that closes the #1 "QA Failed for a non-code reason" hole.** The skill used to only *tell QA to verify* migrations — nothing applied them to the staging DB, so every migration ticket silently depended on a human running the SQL on staging out-of-band. When skipped, QA fails on a no-brainer. Now the skill applies them.

The lovable-staging **preview → staging DB**; qa-mirror → prod DB. For DB-dependent QA on the preview, the migration must be on the staging DB. Apply it here:

1. **Resolve the staging ref.** Use `qa-handoff.json` `stagingDbRef`. If unset, **do not guess** — print the migration files + the apply instruction and ask the user to run them in the staging Dashboard, then continue once they confirm.
2. **For each migration file in the PR diff** (`gh pr diff {NUMBER} --name-only | grep 'supabase/migrations/'`), read its SQL and apply it to the staging ref via the Supabase MCP `apply_migration` (project_id = `stagingDbRef`). The migration files already end with the `schema_migrations` registry insert, so re-runs are idempotent.
3. **Staging carve-out — strip prod-only statements before applying:** a `cron.schedule(...)`/`cron.unschedule(...)` whose body posts to a **prod** `/functions/v1/<slug>` URL must NOT run on staging — the staging cron would fire against the prod edge fn and 404 every tick (the `deliver-newsletters` case, 2026-06-14). Apply the rest of the migration (tables, functions, permissions, RLS) and skip just the prod-URL cron block, noting it in the QA comment as "cron is prod-only at go-live." Everything else (additive DDL, new permission rows, RLS on new tables) applies safely to staging.
4. **Verify before proceeding:** run the confirming SELECT (the one going into the QA comment) against `stagingDbRef`. If it returns 0 rows, STOP — the apply didn't take; surface the error, don't hand off a card that will just fail again.
5. **Drift catch — compare staging vs prod, then route QA accordingly.** This is the step that catches the #1602 class: a migration that reached **prod** (a working-session go-live, or a re-handoff of a previously-QA-failed card) but **never reached staging**, so the lovable-staging preview QA fails for a pure environment reason. For each migration's key object, run a read-only existence check (`execute_sql`, e.g. `to_regclass` / `information_schema.columns` / `pg_proc`) against **both** `stagingDbRef` **and** the prod ref:
   - **Present on staging** → normal path; the QA comment's "applied to staging ✅" claim is now backed by a real verify.
   - **Missing on staging but present on prod** → the feature shipped to prod out-of-band. Either apply to staging now (point 2), OR — if a clean staging apply isn't possible — the QA comment must **route DB-dependent testing to the qa-mirror preview** (which reads the prod DB) with explicit wording: *"Test on the qa-mirror preview, NOT lovable-staging — the staging DB lacks these objects; prod (and therefore qa-mirror) has them."* Confirm qa-mirror is synced first (Step 9 covers the merge). **Never post "applied to staging ✅" off an unverified or skipped apply.**
   - **Missing on both** → it genuinely hasn't landed anywhere; apply to staging (point 2) and re-verify before handing off.

```
Migrations in this PR → applying to staging DB (stagingDbRef) via MCP apply_migration:
  20260614160000_newsletter_foundation.sql        → applied ✅
  20260614160100_newsletter_drain_cron.sql        → applied (cron.schedule skipped: prod-URL, prod-only) ✅
  20260614170000_newsletter_admin_permission.sql  → applied ✅
Verify SELECT → 2 tables, 6 funcs, 1 permission present. Proceeding to QA comment.
```

**Guardrails:**
- **Staging only.** Never apply to the prod ref here — prod is the gated human go-live (kept in the PR description + go-live checklist). Applying additive migrations to the non-prod staging DB is safe and reversible.
- This does NOT replace the `migration-and-writer-deploy-atomically` rule for prod: if the PR couples a constraint/domain migration with an edge fn that writes the column, the *prod* deploy still pairs them. Step 3.5 is purely about unblocking *staging QA*.
- If `apply_migration` errors (e.g. a non-additive migration that conflicts with existing staging state), surface it and ask — don't force.

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

0. **"What changed since your fail"** — **REQUIRED if Step 0 flagged a re-handoff.** Goes first, before the summary. One row per finding from the tester's report, each with its disposition + evidence (see Step 0). Omitting this block is the failure this skill exists to prevent — a re-handoff without it is not a handoff.
1. **Summary table** — one row per change (what, why)
2. **Migration check** — "applied to staging" confirming SELECT block (only if migrations present; the skill already applied them in Step 3.5)
3. **Code verification** — CLI commands (tsc, lint)
4. **UI testing steps** — step-by-step per change, specific viewports/flows
5. **Regression checks** — checklist of related flows that must not break
6. **What was NOT changed** — guardrails / files explicitly untouched

**Re-handoff block (when Step 0 flagged a prior fail) — lead with it:**

```html
<h4>✅ What changed since your fail</h4>
<p>Answering your {DATE} review point-by-point:</p>
<table border="1" cellpadding="4">
  <tr><th>Your finding</th><th>Status</th><th>Evidence</th></tr>
  <tr><td>Label still read "Growth Areas"</td><td>✅ Fixed</td>
      <td>Landed after your review in <code>95272ab7</code>; <code>InterviewReflectionCard.tsx</code> line 126 now reads "What to probe next"</td></tr>
  <tr><td>d3/d9 missing the FAQ token</td><td>☑️ Not a bug — premise was wrong</td>
      <td>FAQ block belongs on d0+d5 only; d3 is a short nudge, d9 the final-note closer. The old guide's "all 4" expectation was incorrect — superseded below.</td></tr>
</table>
```

Use `✅ Fixed` / `☑️ Not a bug — premise was wrong` / `⏭️ Won't fix (out of scope)` as the only three dispositions. Every row cites evidence, never "should be fine now."

**Migration block (when applicable) — the skill already applied to staging in Step 3.5, so this CONFIRMS rather than asks:**

```html
<h3>✅ Migration — Applied to Staging</h3>
<p>This PR's migration(s) were applied to the staging DB during handoff. Sanity-check (should return rows — if 0, ping Tobi, it means the apply didn't take):</p>
<pre>SELECT column_name FROM information_schema.columns
WHERE table_name = '{table}' AND column_name = '{column}';</pre>
<p><strong>You don't need to run any DDL.</strong> Production apply is Tobi's gated go-live step after QA passes.</p>
```

If `stagingDbRef` was unset and Step 3.5 had to prompt the user instead of auto-applying, keep the older "⚠️ Verify Before Testing / if 0 rows ping Tobi" wording — only claim "applied" when the skill actually applied + verified it.

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

### Step 8: Merge PR into Integration Branch (skip if PR already merged or no PR)

If the handoff is for a PR (not a direct push to integration), the PR **must** be merged into the integration branch before qa-mirror sync — otherwise QA pulls stale code. The skill drives the merge so the workflow is one command.

```bash
PR_STATE=$(gh pr view {NUMBER} --json state,mergeable,mergeStateStatus,reviewDecision -q '.state')
if [ "$PR_STATE" = "MERGED" ]; then
  echo "PR already merged — skipping merge step"
elif [ "$PR_STATE" = "OPEN" ]; then
  # Inspect mergeability before acting
  gh pr checks {NUMBER}
  gh pr view {NUMBER} --json mergeable,mergeStateStatus,reviewDecision

  # If checks are red but the failure is pre-existing (e.g. lint debt
  # tracked in a separate ticket), surface the red check to the user
  # and ask before using --admin. NEVER --admin silently.
  gh pr merge {NUMBER} --merge          # merge commit (matches repo convention)
  # OR: gh pr merge {NUMBER} --merge --admin   # only with explicit user OK
fi
```

**Guardrails:**
- Always print the failing-check summary before suggesting `--admin`. The user authorizes admin overrides per PR, never standing.
- Use `--merge` (merge commit) by default — this repo's history shows merge commits, not squash. If the repo uses squash, override with `--squash`.
- If the PR base is not the integration branch (e.g. PR base is `main`), STOP and alert — qa-handoff is for integration→QA flows only.

### Step 8.5: Edge-Function Redeploy Gate (skip if no edge-fn changes)

`qa-mirror` reflects integration-branch *frontend* code, but it hits the same globally-deployed `/functions/v1/*` edge functions as production. If this handoff's diff touches edge fns or `_shared/`, QA will be testing the new UI against the **old** edge-fn code — silent broken handoff. **Gate qa-mirror sync on the redeploy.**

```bash
# Detect edge-fn changes between the live deploy (qa-mirror tip) and what we're
# about to QA (integration branch tip). Use origin refs — local may be stale.
git fetch origin $QA_MIRROR_BRANCH $INTEGRATION_BRANCH

CHANGED_FN_DIRS=$(git diff --name-only origin/$QA_MIRROR_BRANCH...origin/$INTEGRATION_BRANCH \
  -- 'supabase/functions/fn_*/index.ts' 2>/dev/null \
  | awk -F/ '{print $3}' | sort -u)

CHANGED_SHARED=$(git diff --name-only origin/$QA_MIRROR_BRANCH...origin/$INTEGRATION_BRANCH \
  -- 'supabase/functions/_shared/*.ts' 2>/dev/null)

if [ -z "$CHANGED_FN_DIRS" ] && [ -z "$CHANGED_SHARED" ]; then
  echo "No edge-fn changes — skipping deploy gate"
else
  # If _shared/ changed, enumerate every fn that imports the changed file —
  # they all need redeploy because deploys bundle current _shared/ content.
  if [ -n "$CHANGED_SHARED" ]; then
    for shared in $CHANGED_SHARED; do
      base=$(basename "$shared" .ts)
      importers=$(grep -rl "_shared/$base" supabase/functions/ \
        --include='index.ts' 2>/dev/null \
        | awk -F/ '{print $3}' | sort -u)
      CHANGED_FN_DIRS=$(printf '%s\n%s\n' "$CHANGED_FN_DIRS" "$importers" | sort -u | sed '/^$/d')
    done
  fi
fi
```

**If `CHANGED_FN_DIRS` is non-empty, STOP and prompt the user:**

```
⚠ Edge-function redeploy required before QA can test this handoff.

The following functions changed (or import a changed _shared file) since
the last qa-mirror sync. QA must hit the new code, so deploy these first:

  ./scripts/deploy-edge-fn.sh \
    fn_send_candidate_invites \
    fn_resend_skills_invite \
    ...

I'll wait — once deployment succeeds, say "deployed" and I'll continue
with qa-mirror sync (Step 9).
```

**Guardrails:**
- Do NOT proceed to Step 9 until the user confirms the deploy. A premature qa-mirror sync surfaces a UI built against new edge fns + production hitting old ones — false-negative QA.
- The deploy guard (`deploy-edge-fn.sh`) only allows running from `main` / `lovable-staging` / `qa-mirror`. Since we just merged into the integration branch in Step 8, the user can run it from there without `--allow-feature-branch`.
- If the user can't deploy right now (e.g. CI pipeline busy, env access pending), they can answer "skip" and the skill continues with a loud warning in the Step 10 confirmation. Don't silently allow skipping.
- Do not run the deploy command yourself — deploys are user-authorized actions. The skill prompts and waits.

### Step 8.6: Deployed-Where-QA-Tests Gate (backend/API route changes)

**This closes the hole that put 4 cards in QA-Failed at once (Congrats sweep, 2026-07-09).** All four were correct code that failed QA for one reason: the change was on the integration branch but **not deployed to the environment QA actually tested** — two backend Express routes never shipped to prod (`main`), so the live URL 404'd, and QA (testing prod) marked them failed. Steps 3.5 (migrations) and 8.5 (edge fns) cover *their* deploy surfaces; this step covers the **backend/API + separately-deployed-frontend** surface they miss.

Applies when the PR diff touches code that is served by a **separately-deployed runtime** rather than the branch preview — most commonly a backend repo (`backend-restructing`: Express on Vercel, prod deploys from `main`) or any route/endpoint whose live home is a fixed prod domain, not the lovable-staging/qa-mirror preview.

```bash
# Does this handoff touch backend/API route code (not just frontend served by the preview)?
ROUTE_CHANGES=$(gh pr diff {NUMBER} --name-only | grep -iE '(routes?|controller|api|middleware)\.(js|ts)$' )
```

**If `ROUTE_CHANGES` is non-empty, before handing off you MUST answer: "will QA hit this new code where they test?"**

1. **Identify QA's test target for this change.** Backend routes for the Congrats/Vetted stack live at a fixed prod domain (e.g. `backend-restructing-ten.vercel.app`, per `backend-production-url.md`) — NOT the lovable-staging preview. A backend route on the integration branch is invisible to QA until it ships to `main` and Vercel deploys.
2. **Check whether the change is actually in that target.** For a backend repo whose prod deploys from `main`:
   ```bash
   MERGE_SHA=$(gh pr view {NUMBER} --json mergeCommit --jq '.mergeCommit.oid')
   git fetch origin main --quiet
   git merge-base --is-ancestor "$MERGE_SHA" origin/main && echo "IN PROD (main)" || echo "NOT IN PROD — integration only"
   ```
   And, when the route is HTTP-reachable, curl the live endpoint to confirm (a 404 = not deployed):
   ```bash
   curl -sI "https://<prod-domain>/<new-route>" | head -1
   ```
3. **Route the handoff on the result:**
   - **In prod already** → normal path; note the live-URL check passed in the QA comment.
   - **Integration only (prod deploys from main)** → this is NOT a normal QA-handoff. The change won't reach QA without a prod ship. STOP and tell the user: either (a) it rides the next staging→main release (`/merge-to-prod`), or (b) if it's independent and urgent, a targeted cherry-pick to `main` (`/hotfix`-style). Do not move the card to QA claiming it's testable when the live endpoint 404s — that reproduces the exact false-fail this gate exists to prevent.

**Guardrail:** the tell for this whole bug class is *"correct code, marked QA-Failed."* Whenever a card is about to go to QA, the load-bearing question is not "is it merged?" but **"is it live in the environment the tester will open?"** — for migrations (Step 3.5), edge fns (Step 8.5), and now backend/API routes (this step).

### Step 8.7: qa-mirror Drift Detector (skip if `qaMirrorBranch` not detected)

**This is the sentinel for the "qa-mirror got used as a scratch branch" failure class.** `qa-mirror` must equal the integration branch **plus nothing** — but people occasionally merge a feature branch *directly into qa-mirror* to test against prod data ("...into qa-mirror for QA testing", "...for impersonation repro") and never clean it up. Each such merge leaves a **non-merge commit unique to qa-mirror** that never reached the integration branch → off the promotion path → silently at risk of never reaching prod. One such orphan (a `#1850` admin-gate fix) sat latent for days and masked a real access regression (2026-07-11 cleanup). Nothing *triggers* a check, so the drift is invisible until it's painful. This step is that trigger — read-only, cheap, runs every handoff.

**`.deploy.lock`-only commits are filtered separately, not treated as this class of drift.** `scripts/deploy-edge-fn.sh` commits a `.deploy.lock` bookkeeping file on whichever branch it's run from and can push straight to it — a deploy run from `qa-mirror` legitimately leaves a lock commit that never reaches the integration branch, by construction, not because real work is missing (2026-08-21, commit `db074c1d` — flagged as drift, but `lovable-staging`'s own locks for those same functions were already same-or-newer). The detector below skips a candidate only when every file it touches is a `.deploy.lock` AND the integration branch's own copy for that function is same-or-newer — a genuinely stale lock (integration branch missing it or older) still surfaces.

Run **before** the Step 9 merge (so a fresh sync merge doesn't obscure pre-existing orphans). `git cherry` compares by patch-id, so already-promoted commits (even under a different SHA) don't false-positive:

```bash
git fetch origin $QA_MIRROR_BRANCH $INTEGRATION_BRANCH --quiet
# '+' = a patch on qa-mirror NOT present on the integration branch; '-' = already there.
CANDIDATES=$(git cherry origin/$INTEGRATION_BRANCH origin/$QA_MIRROR_BRANCH 2>/dev/null | grep '^+' | awk '{print $2}')

ORPHANS=""
for sha in $CANDIDATES; do
  # .deploy.lock-only false-positive filter (2026-08-21): deploy-edge-fn.sh commits
  # a .deploy.lock per function on whichever branch it's run from and can push
  # straight to that branch — a legitimate deploy from qa-mirror leaves a commit
  # that never reaches the integration branch by construction, not because
  # anything is missing. It's noise, not drift, UNLESS the integration branch's
  # own lock for that fn is actually older (a real gap). Skip only when every
  # changed file is a .deploy.lock AND the integration branch's copy is same-or-newer.
  FILES=$(git show --name-only --format='' "$sha" 2>/dev/null)
  NON_LOCK=$(echo "$FILES" | grep -v '\.deploy\.lock$' | grep -c .)
  if [ -n "$FILES" ] && [ "$NON_LOCK" = "0" ]; then
    STALE=0
    for f in $FILES; do
      NEW_TS=$(git show "$sha:$f" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('deployed_at',''))" 2>/dev/null)
      CUR_TS=$(git show "origin/$INTEGRATION_BRANCH:$f" 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('deployed_at',''))" 2>/dev/null)
      # integration branch missing the file entirely, or strictly older → real gap, don't skip
      if [ -z "$CUR_TS" ] || [ "$CUR_TS" \< "$NEW_TS" ]; then
        STALE=1
      fi
    done
    [ "$STALE" = "0" ] && continue   # superseded on integration branch — not real drift, skip
  fi
  ORPHANS="$ORPHANS
$(git log -1 --no-merges --format='%h %s' "$sha" 2>/dev/null)"
done
ORPHANS=$(echo "$ORPHANS" | sed '/^$/d')

if [ -n "$ORPHANS" ]; then
  echo "⚠ qa-mirror DRIFT — non-merge commits unique to qa-mirror (never reached $INTEGRATION_BRANCH):"
  echo "$ORPHANS"
fi
```

**On finding orphans:** do NOT auto-fix and do NOT block the handoff — surface them to the user with one line: *"qa-mirror has N commit(s) that never reached the integration branch (likely direct-to-qa-mirror test merges). Each is off the promotion path. Want me to triage them (backport the real ones / discard the throwaway) separately, or proceed with the handoff?"* Resolution is a human per-commit decision (some are real unshipped work, some are throwaway `for QA testing`/`for repro` scaffolding), never a blind reset. See `.claude/rules/working-branch.md` (qa-mirror = integration + nothing) and the `qa-mirror-backup-<date>` tag convention for the safe reset flow. If the user says proceed, continue to Step 9 and note the deferred drift in the Step 10 confirmation.

If `git cherry` returns no `+` lines: qa-mirror is clean (integration + nothing) — note "✅ qa-mirror clean (no drift)" and continue.

### Step 9: Sync qa-mirror (skip if `qaMirrorBranch` not detected)

`qa-mirror` points at the live production DB and must reflect the integration branch. Sync after every handoff.

**Always use a worktree** to avoid disturbing the user's current branch state (uncommitted changes, in-flight work):

```bash
WT=$(mktemp -d -t qa-mirror-sync-XXXX)
git worktree add "$WT" $QA_MIRROR_BRANCH
(
  cd "$WT"
  git pull origin $QA_MIRROR_BRANCH --ff-only
  git fetch origin $INTEGRATION_BRANCH
  git merge origin/$INTEGRATION_BRANCH --no-ff \
    -m "Merge remote-tracking branch 'origin/$INTEGRATION_BRANCH' into $QA_MIRROR_BRANCH"
  git push origin $QA_MIRROR_BRANCH
)
git worktree remove "$WT"
```

If merge conflicts: resolve (prefer integration branch) before pushing.
If `qa-mirror` is already up to date: skip and note it.

**Why the worktree:** users are often mid-work on a feature branch with uncommitted changes when /qa-handoff runs. `git checkout qa-mirror` on the main worktree would either fail or risk losing in-flight state. A throwaway worktree is safe and self-cleaning.

### Step 10: Confirm Handoff

```
QA Handoff Complete:
- ✅ Handoff type: first handoff (or: RE-HANDOFF — answered N finding(s) from {TESTER}'s {DATE} fail)
- ✅ PR #{NUMBER} merged into {INTEGRATION_BRANCH} (or: already merged / direct push)
- ✅ QA comment posted on Fizzy #{CARD} (re-handoff: includes the "what changed since your fail" block)
- ✅ Card moved to "{QA_COLUMN_NAME}" column
- ✅ Elvis Muchiri assigned (or: already assigned — skipped)
- ✅ qa-mirror synced with {INTEGRATION_BRANCH} (or: already up to date / no qa-mirror in this repo)
- ✅ qa-mirror drift check: clean (or: ⚠ N orphan commit(s) surfaced — deferred per user)
- ✅ Deployed where QA tests (migrations on staging / edge fns / backend routes live in prod — or: N/A, no such changes)
- 🔗 PR: {PR_URL}
```

### Step 11: Stale-Worktree Nudge (debt control)

qa-handoff is the structural *generator* of stale worktrees: it merges the PR but deliberately never removes the source worktree (QA can fail and you'd need it back; users also return for follow-up commits). So merged-PR worktrees accumulate silently until someone notices dozens. **Do NOT auto-delete the source worktree here** — that destroys QA-fail/return-to-worktree work. Instead, surface the debt at this natural checkpoint.

Only runs if the repo has a `.claude/worktrees/` directory. Cheap, read-only:

```bash
if [ -d .claude/worktrees ]; then
  STALE=$(git worktree list --porcelain | awk '/^worktree /{w=$2} /^branch /{b=$2;sub("refs/heads/","",b); if (w ~ /\.claude\/worktrees\//) print b}' | while read b; do
    [ -n "$b" ] && gh pr list --head "$b" --state merged --json number --jq '.[0].number' 2>/dev/null | grep -q . && echo x
  done | wc -l | tr -d ' ')
  if [ "${STALE:-0}" -gt 10 ]; then
    echo "🧹 ${STALE} merged-PR worktrees in .claude/worktrees/ — stale debt building."
    echo "   Run the sweep in .claude/rules/branch-and-worktree-policy.md (Stale worktree cleanup)."
    echo "   It also prunes the orphaned local branches (the bigger iceberg)."
  fi
fi
```

Print the nudge as the last line of the handoff confirmation when it fires. Threshold 10 is deliberately loose — this is a periodic reminder, not a gate. Never block the handoff on it. The sweep itself stays user-confirmed and lives in the rule file (single source of truth — do not inline the removal logic here).

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
| VettedAI GTM | `03ga0ytgjp086k2scipsjkyeh` | QA to be confirmed | `03ga0ytvaw5wbw2iaq6mf4aua` |

When a new board is added to the ecosystem, add a row here.
