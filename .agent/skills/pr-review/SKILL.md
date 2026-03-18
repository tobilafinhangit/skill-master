---
name: pr-review
description: Reviews GitHub PRs against Fizzy tickets to verify an engineer delivered what was asked. Fetches PR diff + Fizzy card, runs ticket compliance + regression check, prints verdict, and optionally posts to Fizzy. Use when reviewing PRs from engineers before merging.
version: 1.0.0
license: MIT
---

# PR Review

Review a GitHub PR against its Fizzy ticket — verify the engineer delivered what was asked, check for regressions, and post the verdict.

**Announce at start:** "I'm using the pr-review skill to review this PR against its ticket."

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
```

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
   - URLs: `app.fizzy.do/6102589/cards/{NUMBER}`
   - Patterns: `Card #NNN`, `card-NNN`, `Fizzy #NNN`
3. **Search branch name** for leading number: e.g., `337-fix-scoring` → card 337
4. **Not found** → prompt: "No Fizzy card detected. Enter card number (or press Enter to skip ticket compliance):"

If a card number is resolved, fetch it:

```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null

# Card details
CARD_JSON=$(curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json")

# Card comments (often contain the real requirements)
COMMENTS_JSON=$(curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
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

curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
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
- **Account slug**: `6102589`
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
