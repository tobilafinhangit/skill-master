---
name: not-now-triage
description: Triage the "Not Now" (postponed) lane of a Fizzy board — list the auto-postponed cards, classify each (shipped / stale-noise / still-open / human-call), prove "shipped" via target-repo main-ancestry, then close the resolved ones, resurface the still-open ones to a triage column, and leave the ambiguous ones for a human. Use when a board's Not Now lane has accumulated and needs cleaning, or the user says "triage not now", "clean up the postponed cards", "triage the not now section".
---

# Not Now Triage

> **Note:** This skill references `.claude/rules/*.md` files from the original author's private repos — optional deep-dive context, not required. If those files aren't present in your repo, follow the inline instructions in this skill directly.

Clean a Fizzy board's **Not Now** lane. Cards land there by **auto-postpone** (a board's `auto_postpone_period_in_days` — 90 on Bugs, 30 on Congrats — moves idle cards out of their column), so the lane is mostly *resolved-but-never-closed* work plus genuine stale items. The job: close what actually shipped, resurface what's still real, and leave the genuinely-ambiguous for a human — **never bulk-close on vibes**.

**Announce at start:** "I'm using the not-now-triage skill."

## When to use
- A board's Not Now lane has grown (dozens of cards) and needs cleaning.
- User says "triage not now", "clean up the postponed cards", "triage the not now section of <board>".

## Key facts about the lane (don't relearn these)
- **Not Now is NOT a column.** It's the `postponed == true` card flag. (Maybe? = `column == null`; Done = `closed == true`.) See the `/fizzy` skill's "Reading a Board" section.
- **List it via:** `GET /cards.json?board_ids[]={BOARD}&indexed_by=not_now` — the **array** param `board_ids[]=` scopes correctly (singular `board_id=` is silently ignored), and curl MUST use `-g` (globoff) or it mangles the `[]`. Paginate via the `Link: rel="next"` header; assert the fetched count equals `X-Total-Count`.
- **Helper (if present in the repo):** `scripts/fizzy-lane.sh <board_id> not_now table` does all of the above (raw curl, paginates, asserts count). Use it when available; otherwise inline the curl. (Lives in the vettedai repo; not guaranteed in sister repos.)
- Token: `source .env.local` → `$FIZZY_API_TOKEN`. Account is `{FIZZY_ACCOUNT_ID}` (your own account slug).

## Board reference
| Board | Board ID | Triage/intake column (resurface target) |
|-------|----------|-----------------------------------------|
| Bugs | `03fl735hqcd0h1pettl8o94oo` | Technical `03fl737jyf6nx6775618p5zlb` (or Product/Data/Business by topic) |
| Vetted | `03faozjl3gdngcoyzpkr4vf87` | *(look up by name — first column)* |
| Congrats | `03f58rc5c48jorujpxqp5da5b` | *(look up by name)* |

List columns to find the right resurface target: `GET /boards/{id}/columns.json`. Pick the board's intake/grooming lane (Bugs uses topic lanes — Technical for engineering bugs, Product/Data/Business by subject).

---

## Phase 1 — Pull the lane
```bash
source .env.local
./scripts/fizzy-lane.sh <BOARD_ID> not_now table   # or inline the board_ids[]+indexed_by curl
```
Note the total count. If 0, stop — lane is clean.

## Phase 2 — Pattern-group (cheap, no archaeology)
Sort the cards into groups by title pattern. Three groups close on pattern alone — **don't** run git/PR checks on them:
- **Stale monitoring noise** — auto-posted alerts: `[WARNING] Job failure rate is X%`, `[CRITICAL] N cron job(s) failing`. Resolved by definition; if it recurs a fresh alert fires. → **close**.
- **AI troubleshooting reports** — `🔬 Troubleshooting Report: …` diagnostic dumps, typically >90 days old. → **close**.
- **Self-declared dupes** — titles like `dup—delete me`, `[FIXED]` with empty body. → **close** (but `[FIXED]` with a real body still goes through verification).

Everything else = **real work cards** → Phase 3.

## Phase 3 — Verify real cards (fan out, return compact)
> **Context budget.** Reading each card's body+comments + git archaeology is heavy. Keep it OUT of the parent: **fan out subagents**, ~8 cards each (`model: sonnet`), each returning ONLY a compact table row `#N | verdict | evidence (≤12 words)`. Never let a subagent echo card bodies or git logs back.

Each subagent, per card: read body+comments (strip HTML, bound output), then look for fix evidence — a `PR #NNN merged` / QA full-pass comment, a matching commit (`git log --all --since=120d | grep -iE "<2-3 title keywords>"`), or a `.claude/rules/*.md` documenting the fix-class. First-pass verdict ∈ {RESOLVED, STILL-OPEN, UNKNOWN}.

## Phase 4 — THE CLOSE TEST (strict, before closing anything as shipped)
A first-pass "RESOLVED" is **not** enough to close. Prove it — this is `close-requires-main-ancestry.md`:

> **A card may only be closed as shipped when its fix commit is an ancestor of its TARGET repo's `main`.** A Merge-to-Prod column position, a QA full-pass, a `[FIXED]` label, or a rule file existing are **NOT proof** (they mean queued / verified / pattern-learned).

```bash
SHA=$(gh pr view <PR> --repo <owner/repo> --json mergeCommit -q .mergeCommit.oid)
git -C <path-to-target-repo> merge-base --is-ancestor "$SHA" origin/main && echo IN-MAIN || echo NOT-IN-MAIN
```
- **Verify against the repo that OWNS the fix**, not the board's home repo. Detect it from the QA-signoff branch name: `lovable-staging` = Vetted, `verify-deployments` = Congrats, `backend-verify-deployment` = backend. `cd` into THAT repo. "No visibility from here" is not a verdict.
- **Bidirectional:** "no PR in the card" ≠ unshipped — the fix may be in `main` under a keyword-matched commit. Grep `main` before concluding open. Don't close on a soft positive; don't reopen/leave-open on a soft negative — both resolve by finding the actual commit.
- Run this as a **second strict pass** (fan out again, ~8 cards each) over everything the first pass called RESOLVED. It catches false-positive closes — in the 2026-06-29 Bugs run it caught 1 of 24 (#1193, work never built).

Final buckets:
| Bucket | Definition | Action |
|--------|------------|--------|
| ✅ **Close** | strict pass = IN-MAIN, or pattern-group noise/report/dup, or NO-CODE infra-only | `POST /cards/<N>/closure.json` |
| 🔴 **Resurface** | real unfinished work, no fix in main | `POST /cards/<N>/triage.json` {column_id} → triage column + a comment naming what's left |
| ❓ **Human-call** | genuinely ambiguous (cross-repo unverifiable, undecided policy/data call, partial scope) | leave in Not Now; list for the user |

## Phase 5 — Present, then act on confirmation
Print one consolidated table (close N / resurface M / leave K) and **pause**. Closing is reversible (`DELETE /cards/<N>/closure.json` reopens), but bulk mutation still gets one confirmation. On approval:
```bash
# Close
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/<N>/closure.json" -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: not-now-triage/1.0"   # 204
# Resurface (un-postpones + places in column)
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/<N>/triage.json" -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "Content-Type: application/json" -H "User-Agent: not-now-triage/1.0" -d "{\"column_id\": \"$COL\"}"   # 204
# Comment WHY it was resurfaced (HTML body, not markdown)
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/<N>/comments.json" -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "Content-Type: application/json" -H "User-Agent: not-now-triage/1.0" -d "{\"body\": \"<p>Resurfaced from Not Now during triage: …still-open reason… Moved to <b>Technical</b>.</p>"}"   # 201
```
Then re-list the lane to confirm the new count.

## Fizzy gotchas (see `fizzy-api-patterns.md` for the full list)
- `.json` suffix on every action endpoint (closure/triage/comments) or it 422s.
- Comment body is **HTML**, field `body` — markdown renders as a blob.
- macOS bash is 3.2 — **no `declare -A`** (associative arrays fail silently under `set -e`-ish loops, posting empty comment bodies). Use a function or case statement instead.
- `set -euo pipefail` + a `grep` with no match aborts the script — append `|| true` to optional greps (this bit `fizzy-lane.sh`).

## Related
- `close-requires-main-ancestry.md` — the close test (the heart of Phase 4)
- `merge-to-prod` skill — sibling audit logic for the Merge-to-Prod *column*; this skill is the Not Now *lane* analogue
- `/fizzy` — lane semantics + `indexed_by` listing
- `fizzy-api-patterns.md` — endpoint gotchas
