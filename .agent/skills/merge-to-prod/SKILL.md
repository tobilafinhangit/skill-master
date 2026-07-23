---
name: merge-to-prod
description: Opens or updates a staging→main PR covering all Fizzy cards in the "Merge to Prod" column, audits git vs the column (flags shipped cards for closure and premature cards for move-back), and drafts a terse batched PR title/body. Auto-detects integration/target branches and Fizzy board per repo. Use when a batch of tickets has cleared QA + manual UX testing and is ready to ship to production.
version: 1.2.0
license: MIT
---

# Merge to Prod

Ship a batch of ready-to-prod tickets in one PR. Audit the **Merge to Prod** column against git, surface discrepancies, open or update the staging→main PR.

**Announce at start:** "I'm using the merge-to-prod skill."

## When to Use

- Periodically (weekly or on-demand) when tickets have accumulated in the Merge to Prod column
- User says "run the merge to prod workflow", "let's ship what's ready", "merge staging to prod"
- After a QA pass where multiple tickets are marked ready

## Invocation

```
/merge-to-prod              # audit + open/update staging→main PR; asks before Fizzy cleanup
/merge-to-prod --dry-run    # audit only; no PR update, no Fizzy moves
/merge-to-prod --finalize <PR>  # after the PR has merged: close all cards covered by the PR body
```

---

## Phase 1: Auto-Detect Per Repo (No Config Required)

The skill adapts per repo without requiring a config file.

| Item | How it's detected |
|------|-------------------|
| **Integration (staging) branch** | 1) Read `.claude/rules/working-branch.md` or `.claude/rules/integration-branch.md`; 2) else first of `lovable-staging` / `verify-deployments` / `backend-verify-deployment` existing on `origin` |
| **Target (main) branch** | `git symbolic-ref refs/remotes/origin/HEAD` → else `main` → else `master` |
| **Fizzy board ID** | Match repo root name against Repo Reference below → else ask |
| **Merge to Prod column ID** | Lookup `board.id → column ID` from Board Reference → if missing, list columns and match by name "Merge to Prod" (case-insensitive) |
| **QA to be Confirmed column ID** | Same Board Reference → used only for moving premature cards back |

Source the token:
```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null
# → $FIZZY_API_TOKEN
```

### Optional override: `.claude/skills/merge-to-prod.json`

Only needed if auto-detection picks the wrong value:

```json
{
  "integrationBranch": "lovable-staging",
  "targetBranch": "main",
  "fizzyBoardId": "03faozjl3gdngcoyzpkr4vf87",
  "mergeToProdColumnId": "03fxshiw308tfj6zkghfb93z0",
  "qaColumnId": "03fdi5xotshcmiuqk8pj24b23"
}
```

---

## Phase 2: Fetch the Merge to Prod Column

```bash
git fetch origin --quiet

# Fetch ALL cards in the column. Fizzy paginates (first page 15, then escalating 30/50…) and
# returns ONLY page 1 unless you follow the `Link: rel="next"` header / pass ?page=N. A column
# with >15 cards is otherwise SILENTLY TRUNCATED to its first page — this masked a
# 44-card Merge-to-Prod backlog as 15 and is why "I still see cards" recurred.
# ALWAYS paginate to exhaustion; never trust a single unpaginated fetch.
TMP=$(mktemp); echo "[]" > "$TMP"
page=1
while :; do
  PAGE=$(curl -s "https://app.fizzy.do/6102589/boards/$BOARD_ID/columns/$MERGE_COL_ID/cards.json?page=$page" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN" \
    -H "User-Agent: skill-master/merge-to-prod")
  N=$(echo "$PAGE" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
  [ "$N" -eq 0 ] && break
  echo "$PAGE" > "$TMP.page"
  python3 -c "import json; a=json.load(open('$TMP')); b=json.load(open('$TMP.page')); json.dump(a+b, open('$TMP','w'))"
  [ "$N" -lt 15 ] && break          # short page = last page
  page=$((page+1))
done
CARDS=$(cat "$TMP"); rm -f "$TMP" "$TMP.page"

# Sanity check: the fetched count MUST equal the column's X-Total-Count header.
TOTAL=$(curl -s -D - -o /dev/null \
  "https://app.fizzy.do/6102589/boards/$BOARD_ID/columns/$MERGE_COL_ID/cards.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: skill-master/merge-to-prod" \
  | grep -i '^x-total-count:' | tr -dc '0-9')
echo "Fetched $(echo "$CARDS" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))') of $TOTAL cards in the column."
# If these differ, pagination is broken — STOP and fix before auditing, or you
# will finalize a partial column and leave a silent backlog.
```

If the column is empty: stop. There's nothing to ship.

---

## Phase 3: Audit — Classify Each Card

> **Context budget.** The per-card classification below reads the card's body + comments to extract PR refs, then runs git/PR containment checks. Keep that heavy text **out of the parent**: the parent holds only the audit table (`#N → bucket → evidence`). For columns over ~15 cards, **fan out one subagent per card** (or per wave of ~6) — each reads its own card body+comments + runs the containment checks and returns a compact `{card, bucket, evidence_refs}` (a PR number, a SHA — not the card text or git output). The shared `COMMITS`/`staging..main` list can be computed once in the parent and passed to each child.

Compute commits on staging ahead of main:
```bash
COMMITS=$(git log --format='%H|%s' origin/$MAIN..origin/$STAGING)
```

For each card `#N`, classify into one of four buckets.

> **The close test — proof is merge-base ancestry, nothing softer.** A card may ONLY be classified 🟢/✅ (shipped) when its fix commit is an **ancestor of the target repo's `main`**: `git merge-base --is-ancestor <mergeCommit> origin/main`. A "Merge to Prod" column position, a QA full-pass comment, a `[FIXED]` title, or a `.claude/rules/*.md` documenting the fix-class are **NOT proof** — they mean *queued / verified / pattern-learned*, not *in production*. **Verify against the repo that OWNS the fix** (Congrats `vetted-congrats-Flow0.1`, `backend-restructing`), not this board's home repo — detect it from the QA-signoff branch name and `cd` into that repo to run the ancestry check; "no visibility from here" is not a verdict. This is the discipline behind step 2 below — when a finalize/triage pass closes cards as shipped, run the ancestry check, not the column read. (Codified: `.claude/rules/close-requires-main-ancestry.md`.)

**Detection strategy per card** (try in order, stop at first definitive hit):

1. **Exact number match in staging..main** — commit message contains `#N` (word-boundary), `N/-`, `feat/N-`, or `/N/`:
   ```bash
   git log --oneline origin/$MAIN..origin/$STAGING | grep -E "(#$N[^0-9]|/$N[-/]|$N-)"
   ```
2. **PR-link / QA-signoff containment** *(most reliable — branch- and squash-name-agnostic; run this before concluding anything is premature)* — the card body and comments almost always carry an explicit `PR #NNN` and a QA "FULL PASS / sign-off" comment. That PR's merge commit is the authoritative signal, not commit-message tokens:
   ```bash
   # Pull card body + comments, extract every PR number referenced
   PRS=$( { echo "$CARD_DESC"; echo "$CARD_COMMENTS"; } \
          | grep -oE '(PR )?#[0-9]{2,5}|pull/[0-9]{2,5}' | grep -oE '[0-9]{2,5}' | sort -u )
   for PR in $PRS; do
     SHA=$(gh pr view "$PR" --json mergeCommit,state -q \
            'select(.state=="MERGED") | .mergeCommit.oid' 2>/dev/null)
     [ -z "$SHA" ] && continue
     if git merge-base --is-ancestor "$SHA" origin/$MAIN 2>/dev/null; then
       echo "#$N → 🟢 already in main via PR #$PR ($SHA)"; break
     elif git merge-base --is-ancestor "$SHA" origin/$STAGING 2>/dev/null; then
       echo "#$N → ✅ covered: PR #$PR in staging, will ship in this batch"; break
     fi
   done
   ```
   Cards shipped in a *prior* `staging→main` batch land here as 🟢 — the single most common real state of a stale Merge-to-Prod column. A no-code card (manual test/QA task) with a QA full-pass and no PR is also resolved here → 🟢 (completed task, close it).
3. **Already in main (number grep)** — repeat step 1 against `origin/$MAIN` recent history (last ~60 days):
   ```bash
   git log --all --since="60 days ago" --oneline | grep -E "(#$N[^0-9]|/$N[-/])"
   # For each hit, check containment:
   git branch -r --contains <sha> | grep -q "origin/$MAIN"
   ```
4. **Open PR into staging** — a PR targeting `$STAGING` exists whose branch or title references `N`:
   ```bash
   gh pr list --search "$N in:title" --base $STAGING --state open --json number,headRefName
   ```
5. **Keyword fallback** — extract 2-3 distinctive words from the card title (skip priority emojis, type words, "Phase 3", etc.) and grep commit messages across all branches, then check containment.

Buckets:

| Bucket | Definition | Planned action |
|---|---|---|
| ✅ **Covered** | Step 1 or step 2 found a commit/PR-merge in `staging..main` | Include in PR body |
| 🟢 **Already in main** | Step 2 or step 3 found the card's PR-merge / commit is an ancestor of `origin/$MAIN` (shipped in a prior batch, via a differently-named branch, or a no-code task with QA full-pass) | Flag for **closure** (state → done) |
| ❌ **Premature** | Step 4 found an open PR into staging (not yet merged); OR no commits/PRs anywhere **and no QA full-pass on the card** | Flag for **move-back** to QA |
| ❓ **Unknown** | No matches at all | Ask the user before any action |

> **Guardrail — never silently move back a QA-passed card.** If a card carries a QA "FULL PASS / sign-off" comment but steps 1–5 find nothing, do **not** classify it ❌ Premature and move it back to QA. A passed card with no detectable commit is almost always a *finalize gap* (its work shipped in an earlier batch under an unrelated branch/squash name), not missing work. Classify it ❓ Unknown and surface it explicitly for a human decision. Moving a genuinely-shipped, QA-signed card back to QA is the costlier error than leaving it in place one extra cycle.
>
> **Bidirectional corollary — "no PR in the card" is NOT proof of unshipped.** The fix often lives in `main` under a keyword-matched commit the card never references. Before concluding a card is open (or reopening one), grep the target repo's `main` for the fix: `git -C <repo> log origin/main --oneline --since="120 days ago" | grep -iE "<2-3 distinctive title words>"`, then confirm with `git merge-base --is-ancestor <sha> origin/main`. Don't close on a soft positive (column/QA/label); don't reopen on a soft negative (no-PR) — both are resolved by locating the actual commit.

**Also collect infra commits** in `staging..main` that don't match any card — group them under "Infra / chore" in the PR body.

Print the audit as a compact table and pause. Do not mutate anything yet.

---

## Phase 3.5: Prod Migration Check (only if `supabase/migrations/` exists in the repo)

**This closes a real gap: `merge-to-prod` ships *code* to `main` (Vercel) but never applies a DB *migration* to the prod database.** A migration in the batch therefore reaches prod-code with **no prod-DB change applied** — the "code diverges from the DB" trap. Worse, applying a *non-additive* migration to prod before its matching code is on prod breaks the live writer (the #919 26-hour scoring-outage class). This phase surfaces every migration in the batch, classifies it against live prod, and routes it — before the PR is built.

Skip entirely if the repo has no `supabase/migrations/` (root or one level deep). Auto-detect the prod ref from the **Repo Reference** (Vetted `lagvszfwsruniuinxdjb`, Congrats/backend `uvszvjbzcvkgktrvavqe`); if unknown, ask — never guess a ref.

**1. Enumerate the migrations in this batch** (the `staging..main` delta, same window Phase 3 used):
```bash
git diff --name-only origin/$MAIN..origin/$STAGING -- 'supabase/migrations/*.sql' 2>/dev/null
# (also check a one-level-deep path, e.g. congrats/supabase/migrations/, per repo layout)
```
If none → print "No migrations in this batch" and continue to Phase 4.

**2. For each migration, read its SQL and classify it — additive vs non-additive.** This is the load-bearing decision:

| Class | What it looks like | Prod-apply timing |
|---|---|---|
| **Additive** | `ADD COLUMN [IF NOT EXISTS]`, `CREATE TABLE`, `CREATE INDEX`, `CREATE OR REPLACE FUNCTION` (body change that no *stale deployed edge fn* writes against), new RLS/`GRANT`/permission row, new trigger on a new column | Safe to apply to prod **independently** — before, during, or after the code merge. Also safe to **pre-apply for qa-mirror rehearsal** (see `.claude/rules/pre-apply-additive-migration-for-qa-mirror.md`). |
| **Non-additive** | Tightening/replacing a `CHECK`, remapping a text domain (`UPDATE … WHERE col='old'` + CHECK swap), dropping/renaming a column, a data **backfill**, or an RPC/function body change that a **currently-deployed edge fn still writes against** | **Must deploy atomically with its writer.** Do NOT apply to prod ahead of the code, and do NOT pre-apply for rehearsal. Pair the migration apply with the edge-fn deploy in the same go-live step (`.claude/rules/migration-and-writer-deploy-atomically.md`). |

When unsure which class a migration is, treat it as **non-additive** (fail safe). The tell for non-additive is "does an already-live writer's behavior change the instant this lands?" — if yes, it's coupled.

**3. Check whether each migration's key object is already on prod** (read-only; catches "shipped in a prior batch" and "already pre-applied for rehearsal"):
```bash
# Per migration, pick its key object and existence-check it against the PROD ref via
# the Supabase MCP execute_sql (project_id = <prod ref>). Examples:
#   column:  SELECT 1 FROM information_schema.columns WHERE table_name='…' AND column_name='…';
#   table:   SELECT to_regclass('public.<table>');
#   function:SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
#            WHERE n.nspname='public' AND p.proname='<fn>' AND pg_get_functiondef(p.oid) LIKE '%<new-marker>%';
#   registry:SELECT 1 FROM supabase_migrations.schema_migrations WHERE version='<ts>';
```
Use a `<new-marker>` (a column/branch the migration introduces) for `CREATE OR REPLACE` so "present" means *the new body*, not the old one.

**4. Route each migration and add it to the audit output:**

| State | Action |
|---|---|
| **Already on prod** (object present + registry row) | ✅ note "migration already applied to prod (prior batch or pre-applied for rehearsal)" — nothing to do at go-live. |
| **Additive, not on prod** | 📋 add to the PR body's go-live checklist: "Apply `<file>` to prod SQL editor at go-live." Offer to pre-apply now for qa-mirror rehearsal if the user wants (additive-only). |
| **Non-additive, not on prod** | ⚠️ add to the go-live checklist as a **coupled** step: "Apply `<file>` **together with** deploying `<edge fn>` — do not apply ahead of the code." Flag it prominently; this is the one that causes outages if applied early. |

**5. Emit a "⚠️ Migration — Run on Production at go-live" block into the PR body** (Phase 4) listing each not-on-prod migration with its class and the raw DDL, so the DDL is visible at merge time. Never use `supabase db push` (files may have been edited after first apply); apply via the Dashboard SQL editor.

**Guardrails:**
- **Read-only here.** This phase *classifies and reports*; it does not apply anything to prod. Applying additive migrations early for rehearsal is a **separate, user-initiated** step (the pre-apply rule), never an automatic side effect of `merge-to-prod`.
- **The prod ref is per-repo — never hardcode one repo's ref for another** (same discipline as the qa-handoff staging ref).
- This does not replace `qa-handoff` Step 3.5 (which applies to *staging* for QA); this is the *prod* side, at promotion time.

Print the migration audit under the Phase 3 table and pause with the rest of the audit.

---

## Phase 4: Create or Update the staging→main PR

Check for an existing open PR:
```bash
EXISTING=$(gh pr list --base $MAIN --head $STAGING --state open --json number -q '.[0].number')
```

Draft a **terse** PR title + body (keep it short — no filler prose):

**Title:** `chore: merge to prod — YYYY-MM-DD batch (N tickets)`

**Body:**
```markdown
## Staging → Prod batch (YYYY-MM-DD)

Merging N tickets from the **Merge to Prod** column of the {Board Name} board.

### Tickets
- #<num> [Title](https://app.fizzy.do/6102589/cards/<num>) — one-line note
- …

### Infra / chore
- <one-line per infra commit, if any>
```

Execution:
```bash
if [ -n "$EXISTING" ]; then
  gh pr edit $EXISTING --title "$TITLE" --body "$BODY"
else
  gh pr create --base $MAIN --head $STAGING --title "$TITLE" --body "$BODY"
fi
```

On `--dry-run`: print the title + body and the command that would be run. Don't edit or create.

---

## Phase 5: Fizzy Cleanup (ask first)

Show the planned Fizzy actions and pause for confirmation:

```
Planned Fizzy actions:
  - Close (shipped, already in main): #A, #B, #C
  - Move back to "QA to be confirmed": #X, #Y
  - Leave in place (shipping in this PR): #1, #2, #3
```

On confirmation:

**Close shipped cards** — this is a **state change**, not a column move:
```bash
# Fizzy "Done" is card closure. There is no "Done" column with a column_id.
curl -s -X POST "https://app.fizzy.do/6102589/cards/<N>/closure.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
# 204 = success
```

**Move premature cards back to QA to be Confirmed:**
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/<N>/triage.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"column_id\": \"$QA_COLUMN_ID\"}"
# 204 = success
```

**Post a comment on each moved-back card** explaining why (HTML, Fizzy-friendly):
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/<N>/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": {"body": "<p>Moved back from <b>Merge to Prod</b> during the YYYY-MM-DD batch (PR #NNN). PR #MMM is still open — code is not in integration branch yet. Re-test once merged.</p>"}}'
```

Leave **Covered** cards in Merge to Prod — they stay there until the PR actually merges. Use `--finalize` later.

---

## Phase 6: Finalize (separate invocation after merge)

`/merge-to-prod --finalize <PR_NUMBER>` runs after the PR has been merged to main.

```bash
# 1. Verify the PR is merged
gh pr view $PR_NUMBER --json state,mergedAt --jq '.state'
# Expect: "MERGED". If "OPEN", stop.

# 2. Extract ticket numbers — ONLY from bullet lines under "### Tickets",
#    NOT from anywhere in the body. Otherwise GitHub PR numbers like (#541),
#    parenthetical refs like "Card #644", and related-ticket refs like
#    "(from #318)" all get matched and wrongly closed.
TICKETS=$(gh pr view $PR_NUMBER --json body -q .body \
  | awk '/^### Tickets[[:space:]]*$/ {flag=1; next} /^### / {flag=0} flag' \
  | grep -oE '^- #[0-9]+' | grep -oE '[0-9]+' | sort -u)

# 3. Print before closing so a wrong list is visible before mutation
echo "About to close the following tickets:"
for N in $TICKETS; do echo "  - #$N"; done

# 4. Close each
for N in $TICKETS; do
  curl -s -X POST "https://app.fizzy.do/6102589/cards/$N/closure.json" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN"
done
```

Confirm with a summary:
```
Finalize complete for PR #NNN:
  - Closed N tickets: #A, #B, …
```

---

## Confirmation Message (end of Phase 5)

```
Merge to Prod — done for this batch

PR: #<NNN> — {title}
  Status: OPEN, awaiting review

Shipping (N cards, stay in Merge to Prod):
  #1, #2, …

Closed (already in main, N cards):
  #A, #B, …

Moved back to QA to be confirmed (N cards):
  #X, #Y — reason per card

Next: after PR merges, run `/merge-to-prod --finalize <NNN>` to close the shipping cards.
```

---

## Fizzy API Reminders

- Always `.json` suffix on action endpoints (closure, triage, comments, assignments) — missing suffix returns 422 or 401
- **"Done" is card closure** — `POST /cards/<N>/closure.json` — NOT a column move. Fizzy's default "Done" bucket is a status field, not a column with an ID.
- Mutations return `204 No Content` on success; creations return `201 Created`
- Token lives in `.env.local` as `$FIZZY_API_TOKEN`. Never hardcode.
- Comment body is HTML — markdown is ignored and renders as a blob
- Card body field is `description`, comment body field is `body` (they differ)
- **Column listings paginate with an escalating page size (15→30→50…).** `GET .../cards.json` returns only the first page unless you follow `Link: rel="next"` / pass `?page=N`. The response carries `X-Total-Count`. Any column listing MUST loop pages to exhaustion and assert the fetched count equals `X-Total-Count` — never stop on the first <15 page; a single fetch silently truncates a >15-card column (the cause of a 44-card backlog reading as 15). Use the per-column endpoint — `cards.json?board_id=` is silently ignored. Full rules: "Reading a Board — AUTHORITATIVE" in `/fizzy`.
- **Column membership ≠ this repo.** A board's Merge-to-Prod column can hold cards whose work ships via sister repos (Congrats / backend). Detect repo via each card's QA-signoff branch name (`lovable-staging`=Vetted, `verify-deployments`=Congrats, `backend-verify-deployment`=backend) before classifying; never judge a sister-repo card against this repo's git, and never close it from here.
- **Title-verify before trusting a PR number.** Card numbers and PR numbers collide across repos and a comment often cites *another* ticket's PR. Confirm the candidate PR's title names the ticket (`fix(#N)`/`Fizzy #N`) before using its merge commit as proof-of-ship.

---

## Repo Reference

| Repo directory name | Integration branch | Target branch | Board |
|---|---|---|---|
| `vettedai-audition-supabase-version` | `lovable-staging` | `main` | Vetted |
| `vetted-congrats-Flow-GENEROUS` | `verify-deployments` | `main` | Congrats |
| `backend-restructing` | `backend-verify-deployment` | `main` | Congrats (shared) |

Match by directory basename (`basename "$(git rev-parse --show-toplevel)"`). If no match: ask the user.

---

## Board Reference

Used by Phase 1 to derive column IDs from the board.

| Board | Board ID | Merge to Prod Column ID | QA to be Confirmed Column ID |
|---|---|---|---|
| Vetted | `03faozjl3gdngcoyzpkr4vf87` | `03fxshiw308tfj6zkghfb93z0` | `03fdi5xotshcmiuqk8pj24b23` |
| Congrats | `03f58rc5c48jorujpxqp5da5b` | *(lookup by name on first run)* | `03f58rxrkofln7o86yce47gvk` |
| Bugs | `03fl735hqcd0h1pettl8o94oo` | *(lookup by name on first run)* | `03fnl3h1becpuazzhahxbn208` |

**Lookup by name** (fallback when column ID not known):
```bash
curl -s "https://app.fizzy.do/6102589/boards/$BOARD_ID/columns.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  | python3 -c "import json,sys; [print(c['id']) for c in json.load(sys.stdin) if c['name'].lower()=='merge to prod']"
```

When a new board's Merge to Prod column ID is discovered, add it to this table (edit this file + commit + distribute).

---

## Team Reference

| Person | Role | User ID |
|--------|------|---------|
| Tobi Lafinhan | Owner | `03f58r3y17c4p4ucpvaf7mn5g` |
| Elvis Muchiri | QA Lead | `03fcio1h8spstjpkc82vciugk` |
