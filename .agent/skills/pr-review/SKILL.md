---
name: pr-review
description: Reviews GitHub PRs against Fizzy tickets to verify an engineer delivered what was asked. Fetches PR diff + Fizzy card, runs ticket compliance + regression check, prints verdict, and optionally posts to Fizzy. Single PR or bulk (review a whole "PR Open" column / all open PRs in one parallel pass). Use when reviewing PRs from engineers before merging.
version: 1.2.0
license: MIT
---

# PR Review

> **Note:** This skill references `.claude/rules/*.md` files from the original author's private repos — optional deep-dive context, not required. If those files aren't present in your repo, follow the inline instructions in this skill directly.

Review a GitHub PR against its Fizzy ticket — verify the engineer delivered what was asked, check for regressions, and post the verdict.

**Announce at start:** "I'm using the pr-review skill to review this PR against its ticket."

## Review Hygiene (read this first)

Every invocation begins with a fresh `gh` and Fizzy API GET — never reuse drafts, comments, or analysis from a prior session.

- ❌ Do NOT read pre-existing files under `.claude/tickets/`, `.claude/notes/`, `/tmp/*review*`, or any path that looks like a previously-authored draft for this PR or ticket. Even files matching the current PR/card number are stale by definition — the source of truth is the live API.
- ❌ Do NOT reuse a verdict, issue list, or comment body that was generated for a different PR earlier in this chat or a previous session. Posting #712's findings on #740 is the canonical failure mode this rule prevents (Fizzy #794, May 2026).
- ✅ Always start from `gh pr view --json ...` + `gh pr diff` + a Fizzy API GET of the card and its comments (the existing "Resolve Inputs" workflow). Synthesize fresh.
- ✅ If you find an existing draft file matching the current target, surface it to the user as a warning ("there's a draft at `.claude/tickets/<x>.md` from an earlier session — ignoring it; ask if you'd like me to delete it") but do not read or reuse it.
- ✅ Don't gloss the verdict. If there are action items, enumerate them explicitly even if minor — user pushback like "so nothing is wrong?" is the signal that the verdict was over-summarized.

## When to Use

- When reviewing a PR from an engineer before merging
- When the user says "review this PR", "check this PR against the ticket", "verify this PR"
- Before merging feature branches into `verify-deployments` / `lovable-staging`

## Invocation

```
/pr-review                          # Zero-arg: auto-detect PR + card from current branch
/pr-review 342                      # PR number, auto-detect card
/pr-review 342 --card 337           # PR number + explicit Fizzy card
/pr-review "Fix composite score"    # PR title search + auto-detect card

# Bulk (see "Bulk Mode" below)
/pr-review bulk                     # Union: "PR Open" Fizzy column + all open PRs on the integration branch
/pr-review bulk --source column     # Only the "PR Open" column's cards
/pr-review bulk --source open-prs   # Only open GitHub PRs targeting the integration branch
/pr-review bulk 342 351 360         # Only this explicit set of PRs
/pr-review bulk --author oussama    # Only open PRs by one author
```

`bulk` reuses the single-PR review (Steps 1–3) per PR, fanned out in parallel, then aggregates. Everything below the line is the single-PR path; Bulk Mode wraps it.

---

## Workflow

### Step 1: Resolve Inputs

Resolve the PR and Fizzy card. Ask only when auto-detection fails.

#### 1a. Resolve PR

Priority order:

1. **Number or URL given** → use directly
2. **Title string given** → search open PRs:
   ```bash
   gh pr list --state open --json number,title,headRefName --limit 20
   ```
   Match the title (case-insensitive substring). If multiple matches, show them and ask the user to pick one. If zero matches, search closed PRs too.
3. **No argument given** → detect from current branch:
   ```bash
   gh pr view --json number,title,baseRefName,headRefName,url,state 2>/dev/null
   ```
   If no PR exists for the current branch, tell the user and stop.

#### 1b. Fetch PR metadata

```bash
# Structured metadata
gh pr view {NUMBER} --json number,title,body,baseRefName,headRefName,url,state,additions,deletions,changedFiles,mergedAt

# Full diff
gh pr diff {NUMBER}
```

**Guards:**
- PR not found → fail: "PR #{N} not found. Recent open PRs: ..." (list 5 recent)
- PR already merged → warn: "PR #{N} is already merged. Running review anyway (merge action disabled)."
- PR has no diff (0 changed files) → fail: "PR #{N} has no changes to review."

#### 1c. Resolve Fizzy Card

Priority order:

1. **`--card N` given** → use directly
2. **Search PR body** for Fizzy card references:
   - URLs: `app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}`
   - Patterns: `Card #NNN`, `card-NNN`, `Fizzy #NNN`
3. **Search branch name** for leading number: e.g., `337-fix-scoring` → card 337
4. **Not found** → prompt: "No Fizzy card detected. Enter card number (or press Enter to skip ticket compliance):"

If a card number is resolved, fetch it:

```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null

# Card details
CARD_JSON=$(curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json")

# Card comments (often contain the real requirements)
COMMENTS_JSON=$(curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json")
```

**Guards:**
- Card not found (404) → warn, skip ticket compliance
- Card has no description → warn: "Card #{N} has no description — using title + comments only. Compliance accuracy may be reduced."
- Fizzy API down (5xx / timeout) → warn: "Fizzy unreachable — skipping ticket compliance. Running code-only review."

#### 1d. Display Resolved Context

Print a summary so the user can bail if something is wrong:

```
PR:   #342 "Fix composite score fallback" (7 files, +120 -45)
Card: #337 "🔴 Composite score shows 0% for multi-stage candidates"
Base: lovable-staging
```

If no card: `Card: (none — code-only review)`

Pause briefly. If the user says "wrong" or "stop", abort.

### Step 2: Review (Single Subagent, Two Phases)

Spin up **one subagent** with codebase access (Grep, Glob, Read). The subagent runs two sequential phases that share context.

> **Empty-return guard (2026-08-25, #3447):** The subagent MUST return its verdict. Verify it produced a **non-empty, structured** result before you act on it. If it returns empty/truncated/`{}` — do **NOT** fill the gap by grading the work yourself. The whole point of this skill is a reviewer who is not the author; a self-verdict is a rubber-stamp by the author and silently defeats every guardrail above. Instead: retry the subagent once; if it returns empty again, **stop** and surface it explicitly — *"`{review}` subagent returned empty twice; I did not self-review. Worth trying it as `{general}` or manually before merging."* (Root cause seen in the wild: a subagent agent-type pinned to a paid model that returns nothing on invocation. Verify the agent type/model returns at all.) A review that didn't happen is reported, never faked.

#### Phase A: Ticket Compliance

**Skip this phase if no Fizzy card was resolved.**

Parse the ticket specification from: card title + card description (HTML body) + all comment bodies.

For each identifiable requirement in the ticket:
- Check if the PR diff contains corresponding changes → **Pass** / **Partial** / **Miss**
- Note which files address each requirement

Additionally check:
- **Scope creep:** Are there changes in the PR NOT mentioned in the ticket? Flag them (not necessarily bad — but worth noting).
- **Verification steps:** If the ticket includes a "Definition of Done" or verification steps (grooming-architect format), check if the PR satisfies them.
- **Technical guardrails:** If the ticket specifies constraints ("do NOT modify X", "must use Y pattern"), verify compliance.

Output: A structured compliance checklist.

#### Phase B: Regression & Anti-Pattern Check

**Always runs, even without a Fizzy card.**

Instruct the subagent to follow the methodology from `pr-verification` (read `submodules/skill-master/.agent/skills/pr-verification/SKILL.md` for the full checklist). Specifically:

1. **Categorize changes** by risk: Added (low), Modified (medium), Deleted (high)
2. **Detect destructive patterns** in Modified/Deleted files:
   - Removed exports still used by consumers
   - Changed function signatures without updating callers
   - Deleted files still imported elsewhere
   - Renamed without migration
3. **Discover consumers** of any modified/deleted exports using Grep
4. **CLAUDE.md anti-pattern scan** (project-specific value-add):
   - Read the "Anti-Patterns (DO NOT)" section of CLAUDE.md
   - Check if any changed files introduce documented anti-patterns
   - Check `.claude/rules/` for rules relevant to the changed files

**Large diff handling:** If the PR changes >500 lines, use `gh pr diff --stat` first to triage. Deep-read only Modified and Deleted files. Summarize Added files from their stat line.

Output: A risk assessment with specific file references.

### Step 3: Generate Verdict

Combine Phase A and Phase B results into a verdict.

#### Verdict Types

| Verdict | Criteria |
|---------|----------|
| **Approved** | All ticket requirements addressed (or no ticket). No regressions. No anti-pattern violations. |
| **Needs Changes** | Partial delivery, regressions detected, or anti-pattern violations. Includes specific action items. |

#### Terminal Output (Primary)

This is the main output the user sees. Be structured and scannable:

```
PR Review — #342 → Card #337
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Verdict: ✅ Approved

Ticket Compliance (3/3):
  ✅ Add > 0 guard for composite_score_ai
  ✅ Update CandidateDetailPage sorting
  ✅ Update useCandidateInsights comparators

Scope Notes:
  ℹ️ Also updated MarketTable.tsx (not in ticket — minor related fix)

Regression Check:
  🟢 7 files changed, all modifications additive
  🟢 No removed exports
  🟢 No consumer breakage detected

Anti-Pattern Scan:
  🟢 No CLAUDE.md violations in changed files

Recommendation: Safe to merge.
```

For "Needs Changes" verdicts, include specific action items:

```
Verdict: ⚠️ Needs Changes

Ticket Compliance (2/3):
  ✅ Add > 0 guard for composite_score_ai
  ✅ Update CandidateDetailPage sorting
  ❌ Update useCandidateInsights comparators — not found in diff

Regression Check:
  🟡 Removed export `formatScore` from utils/scoring.ts
     → Still imported by: TopMatchHeroCard.tsx:12, MarketTable.tsx:45

Action Items:
  1. Address missing requirement: useCandidateInsights comparators
  2. Restore `formatScore` export or update 2 consumers
```

### Step 4: Post to Fizzy (Opt-In)

After printing the terminal verdict, prompt:

**"Post this verdict to Fizzy card #{N}? [Y/n]"**

If the user confirms (or if no Fizzy card exists, skip this step entirely):

```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null

curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"comment": {"body": "<h2>PR Review — #...</h2>..."}}'
# 201 = success
```

#### Fizzy Comment Format

Keep it concise — engineers skim. Use HTML (Fizzy renders HTML, not Markdown).

```html
<h2>PR Review — #{PR_NUMBER}</h2>
<p><strong>Verdict: ✅ Approved</strong></p>

<h3>Ticket Compliance</h3>
<ul>
  <li>✅ Add &gt; 0 guard for composite_score_ai</li>
  <li>✅ Update CandidateDetailPage sorting</li>
  <li>✅ Update useCandidateInsights comparators</li>
</ul>

<h3>Scope Notes</h3>
<ul>
  <li>Also updated MarketTable.tsx (not in ticket — minor related fix)</li>
</ul>

<h3>Regression Check</h3>
<p>🟢 7 files changed, all additive. No consumer breakage. No anti-pattern violations.</p>

<hr>
<p><em>Generated by pr-review skill</em></p>
```

For "Needs Changes" verdicts, add an "Action Items" section with numbered items.

**If Fizzy comment posting fails:** Print "Could not post to Fizzy (HTTP {status}). Verdict was printed above." Do not retry or fail the skill.

### Step 5: Confirm to User

```
PR Review Complete:
- PR #342: ✅ Approved (or ⚠️ Needs Changes)
- Card #337: verdict posted to Fizzy (or: no Fizzy card)
- Next: merge PR and run /qa-handoff 337 when ready
```

---

## Bulk Mode

Review many PRs in one pass. `/pr-review bulk` reviews the **union** of two sources; flags narrow it. Bulk reuses the single-PR pipeline (Steps 1–3) per PR — it does not invent a second review method.

### Context budget (read before a big batch)

The parent (this) context must hold only the **work-list** and the **compact verdict** each PR returns — never a PR diff, a card body, or a comment thread. Those live only inside the per-PR subagent (B2), which fetches its own and returns `{pr, card, verdict, …, headline}`. A diff is the largest single payload in a review; a parent that reads even a few directly will not survive a 20-PR batch. Two consequences:
- **B1 stays lean:** resolve the work-list from light fields (number, title, branch). Match cards to PRs by **branch prefix first**; pull a PR/card **body** only for the leftovers prefix-matching can't resolve — never slurp every body into the parent.
- **Wave + checkpoint:** run ~6 subagents at a time; append each wave's verdicts to a scratchpad file and aggregate from the file, not from memory. For >15 PRs (or any run you want resumable), drive the fan-out with the **Workflow tool** — one pipeline item per PR, `schema:` on each agent to force the compact verdict shape — instead of ad-hoc subagents.

Measure a bulk run with `submodules/skill-master/scripts/measure-skill-run.ts --cards N` (deno) — watch **parent peak context**; it should stay ~flat as PR count grows.

Auto-detect per repo from the **Repo Reference** below: the integration branch and the board. Match by `basename "$(git rev-parse --show-toplevel)"`; if no row matches, ask the user.

### B1. Resolve the batch

**Source `open-prs`** — every open PR targeting the integration branch:
```bash
INTEGRATION=...   # from Repo Reference (e.g. verify-deployments)
gh pr list --state open --base "$INTEGRATION" \
  --json number,title,headRefName,author --limit 100   # no `body` — keeps the parent lean (see Context budget)
```
If the repo also takes PRs straight to `main`, run a second call with `--base main` and union the results.

**Source `column`** — cards sitting in the "PR Open" column:
```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null
BOARD_ID=...      # from Repo Reference
# Resolve the column ID by name (the column may be "PR Open", "In Review", "Code Review")
PR_OPEN_COL=$(curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/$BOARD_ID/columns.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: skill-master/pr-review" \
  | python3 -c "import json,sys; print(next((c['id'] for c in json.load(sys.stdin) if c['name'].lower() in ('pr open','prs open','in review','code review')), ''))")
# Then fetch ALL cards in that column — PAGINATE. Follow `Link: rel="next"` (page size escalates
# 15→30→50; do NOT stop on the first <15 page) and assert fetched count == X-Total-Count.
# Full paginator + scoping rules: see "Reading a Board — AUTHORITATIVE" in /fizzy.
```
A single unpaginated column fetch silently truncates to its first page — always page to exhaustion
and check the `X-Total-Count` header (`cards.json?board_id=` is silently ignored; use the per-column
endpoint above). For each card, find its PR by matching the **card number** against the open-PR list by **branch prefix** (`NNN-...`); only if the prefix doesn't resolve, fetch that one PR's body and look for `Card #NNN` / `cards/NNN` — don't pull every PR body into the parent. A card with **no matching open PR** → record it as "no PR found" (usually: not pushed yet, or already merged) and skip the review — don't fabricate one.

**Narrowing:** `--source column|open-prs` (one source only), explicit numbers (`bulk 342 351` → review just those), `--author <login>` (filter the open-PR list by `author.login`).

**Build the work list** — a deduped set of `{pr, card}` pairs keyed by PR number. Print it and pause before reviewing:
```
Bulk review — 6 PRs (integration: verify-deployments)
  #342 → Card #337  "Fix composite score"
  #351 → Card #344  "Withdraw application"
  #360 → (no card)  "Bump deps"
  ...
  ⚠️ Card #349 in "PR Open" has no open PR — not pushed? (will skip)
```
If the user says stop, abort.

### B2. Fan out — one subagent per PR, in parallel

Launch the Step 2 review (Phase A compliance + Phase B regression) as **independent parallel subagents, one per PR** — never sequentially, never sharing context. Each subagent:
- Receives ONLY its own PR number + resolved card number. It runs its own fresh `gh pr diff` + Fizzy GET (Review Hygiene applies per-PR).
- Returns a structured verdict keyed to its PR: `{pr, card, verdict, compliance[], regressions[], antipatterns[], action_items[], headline}`.

**Cross-PR contamination is the #1 bulk risk.** No subagent may see another PR's diff or findings, and every verdict must carry its own PR number. This is precisely the failure `Review Hygiene` guards against (#794: #712's findings posted on #740) — bulk amplifies it. **Self-check:** if a verdict's file references don't appear in that PR's own diff, discard it and re-run that one PR.

**Concurrency:** cap ~6 subagents at once; queue the rest. For large batches (>15 PRs) or when you want deterministic, resumable fan-out, drive it with the **Workflow tool** (one stage per PR) instead of ad-hoc subagents.

### B3. Aggregate (summary first)

Print a scannable summary table, then the full single-PR detail block **only** for each ⚠️ Needs Changes (approved ones stay one line):
```
Bulk PR Review — 6 PRs (integration: verify-deployments)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PR     Card    Verdict           Headline
#342   #337    ✅ Approved        3/3 reqs, additive only
#351   #344    ⚠️ Needs Changes   1 missing req, 1 removed export
#360   (none)  ✅ Approved        dep bump, no consumers affected
...
Totals: 4 approved · 2 need changes · 1 PR-less card (#349)
```
Don't gloss: every ⚠️ must list its action items explicitly (Review Hygiene applies to the aggregate too).

### B4. Post to Fizzy (opt-in, after the summary)

**Bulk never auto-posts.** After the summary, prompt:

**"Post verdicts to Fizzy? [all / pick / none]"**
- `all` → post each PR's verdict to its card (skip PR-less and card-less ones).
- `pick` → list the PRs that have cards; user names which to post.
- `none` → terminal-only, done.

Post with the existing Step 4 HTML format — one comment per card. Print a per-card result line. A failed post warns and never aborts the batch.

---

## Graceful Degradation

| Failure | Behavior |
|---------|----------|
| No Fizzy card found | Skip ticket compliance, run code-only review |
| Fizzy API down / 5xx | Skip card fetch + posting, print review to terminal only |
| Card has no description | Use title + comments as context, warn about reduced accuracy |
| PR already merged | Run review, disable merge suggestion in "Next" line |
| Large diff (>500 lines) | Stat-first triage, deep-read only M/D files |
| `gh` rate limited / auth failure | Fail with clear message: "GitHub CLI error: {message}" |
| Fizzy comment post fails | Print warning, do not retry. Verdict is already in terminal. |
| PR not found | Fail with recent open PRs listed as suggestions |

---

## Relationship to Other Skills

| Skill | Relationship |
|-------|-------------|
| `pr-verification` | Phase B references its methodology. `pr-verification` stays available standalone for PRs without tickets. |
| `qa-handoff` | User chains separately after merging. Not invoked by `pr-review`. |
| `ticket-review` | Reviews tickets *before* engineering starts. `pr-review` reviews PRs *after* engineering delivers. Complementary pair. |
| `impact-analysis` | If Phase B finds modified shared hooks/utils with runtime side effects, recommend running `/impact-analysis` as a follow-up. |
| `fizzy` | Reuse card-fetching and comment-posting patterns. |

---

## Fizzy API Reminders

- **Always use `.json` suffix** on action endpoints (comments, triage, assignments)
- **Token**: `source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null` → `$FIZZY_API_TOKEN`
- **Account slug**: `{FIZZY_ACCOUNT_ID}` (your Fizzy/Basecamp account slug — see the setup note in the `fizzy` skill)
- **Comments endpoint**: `POST /cards/{NUMBER}/comments.json` with `{"comment": {"body": "..."}}`
- **Card details**: `GET /cards/{NUMBER}.json`
- **Card comments**: `GET /cards/{NUMBER}/comments.json`
- HTML in comments: use `<h2>`, `<h3>`, `<ul>/<li>`, `<table>`, `<code>`, `<pre>` — Fizzy renders HTML

## Error Handling

| Error | Action |
|-------|--------|
| `gh` not authenticated | "Run `gh auth login` first" |
| 401 on Fizzy | "Check $FIZZY_API_TOKEN — run `source .env.local`" |
| 404 on Fizzy card | "Card #{N} not found — skipping ticket compliance" |
| 404 on GitHub PR | "PR #{N} not found" + list recent open PRs |
| Empty PR diff | "PR #{N} has no changes to review" — stop |
| Subagent timeout | Print partial results collected so far |

## Team Reference

| Person | Role | User ID |
|--------|------|---------|
| Elvis Muchiri | QA Lead | `03fcio1h8spstjpkc82vciugk` |
| Oussama | Backend | `03f5clrwhb0jpi7h8yxhzfc2i` |
| Tobi Lafinhan | Owner | `03f58r3y17c4p4ucpvaf7mn5g` |

## Board Reference

| Board | Board ID |
|-------|----------|
| Product | `03feaz5rc2t60wkn2rvjkhy6b` |
| Bugs | `03fl735hqcd0h1pettl8o94oo` |
| Vetted | `03faozjl3gdngcoyzpkr4vf87` |
| Congrats | `03f58rc5c48jorujpxqp5da5b` |
| VettedAI GTM | `03ga0ytgjp086k2scipsjkyeh` |

## Repo Reference

Per-repo auto-detect for Bulk Mode. Match by `basename "$(git rev-parse --show-toplevel)"`.

| Repo directory name | Integration branch | Board |
|---|---|---|
| `vettedai-audition-supabase-version` | `lovable-staging` | Vetted |
| `vetted-congrats-Flow-GENEROUS` | `verify-deployments` | Congrats |
| `backend-restructing` | `backend-verify-deployment` | Congrats (shared) |
| `vetted-gtm-frontend` | `main` | VettedAI GTM |

The "PR Open" column ID is resolved by name on the board at run time (see Bulk Mode B1) — it's not hardcoded. If no row matches the current repo: ask the user for the integration branch + board.
