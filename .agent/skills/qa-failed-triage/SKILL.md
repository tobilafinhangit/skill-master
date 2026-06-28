---
name: qa-failed-triage
description: Sweeps a board's "QA Failed" column, and for each card classifies WHY it failed, verifies that classification against ground truth (git ancestry, deployed-vs-prod, DB state, project rules), then routes it to the right remedy. Most QA-Failed cards are NOT "the code is wrong, re-review it" — they're stale checkouts, environment drift, deploy gaps, or rule-misreads. Use when a batch of cards is stuck in QA Failed and you want to clear them efficiently as the senior engineer.
version: 1.1.0
license: MIT
---

# QA-Failed Triage

Sweep the "QA Failed" column. For each card: **classify the failure → verify the classification against ground truth → route to the remedy.** You are the senior here — your job is to find what actually broke, not to re-run a review.

**Announce at start:** "I'm using the qa-failed-triage skill to sweep the QA-Failed column."

## The core insight (read this first)

A "QA Failed" card is rarely "the engineer's code is wrong." Across real sweeps, the dominant causes are:

1. **Stale checkout** — QA tested an old local branch; the work IS present and correct on the integration branch HEAD. (False-fail.)
2. **Code done, blocked downstream** — code is merged and often already live in prod; the blocker is environment drift (e.g. test-mode Stripe price IDs, unseeded data) or an un-applied migration / un-deployed edge fn. (Not a code problem.)
3. **Rule-misread** — QA flagged correct-by-design behavior as a regression (e.g. a hard-gate modal on a wallet operation, which `soft-gate-ui-hard-gate-wallet.md` *requires*).
4. **Merge gap** — the PR shows MERGED on GitHub but the integration branch was rewritten after (Lovable force-push), dropping it. (Real, but the remedy is re-merge, not review.)
5. **Genuine code bug** — a real defect remains. **This is the minority.**
6. **Not a PR at all** — a manual spike / validation task that was never executed. A code review can't touch it.

**Blanket-running `/pr-review` on every card is the wrong tool.** It re-reviews already-approved code and misses the real blocker. The product of this skill is the *verification* that tells classes apart, then the *routing*.

**Do not trust QA's framing.** "Hard-gate modal is a regression," "files don't exist on staging," "pricing is broken" are *symptoms reported from a possibly-drifted environment*. Verify each against ground truth before acting.

## Inputs

- **Board + "QA Failed" column — auto-detect per repo, never hardcode.** Don't assume a board; resolve it from the repo you're in:
  1. **Board ID** — match `basename "$(git rev-parse --show-toplevel)"` against the Board Reference below → if no match, ask the user which board.
  2. **QA-Failed column ID** — take it from the Board Reference if known; otherwise list the board's columns and match by name (case-insensitive, contains both `qa` and `fail`):
     ```bash
     curl -s "https://app.fizzy.do/6102589/boards/$BOARD_ID/columns.json" \
       -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: skill-master/qa-failed-triage" \
       | python3 -c "import json,sys; [print(c['id'], c['name']) for c in json.load(sys.stdin) if 'qa' in c['name'].lower() and 'fail' in c['name'].lower()]"
     ```
     When you discover a new board's QA-Failed column ID, add it to the Board Reference (edit this file + distribute).
- Fizzy creds: `source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null` → `$FIZZY_API_TOKEN`. All Fizzy mechanics (`.json` suffix, `triage.json` to move, `assignee_id`, HTML comment bodies, pagination) per `/fizzy` and `.claude/rules/fizzy-api-patterns.md` — don't re-derive them.
- Phase 3 ground-truth checks are repo-relative: resolve the **integration branch** per repo (`.claude/rules/working-branch.md` / `integration-branch.md`, else the first of `lovable-staging` / `verify-deployments` / `backend-verify-deployment` on `origin`) and cite *that repo's* `.claude/rules/`. The rule filenames named in later phases are Vetted/Congrats examples — substitute the equivalents for whatever repo you're in.

## Batch discipline — keep the parent context small (read before sweeping)

QA-Failed cards are long: full descriptions + paginated comment threads + the per-card ground-truth dumps (git output, prod query results, edge-fn bodies). If the **parent** (this) context reads all of that for every card, the window fills and the sweep dies mid-column — worse on big or wordy columns, which is exactly when you reached for this skill. Two rules make a sweep survive any column size:

1. **Heavy text lives only in per-card subagents, never in the parent.** The parent holds a lean work-list and the compact verdict each child returns — never a full card body, a full comment thread, a diff, or a raw query result. Text that enters the parent context is billed every turn for the rest of the sweep and cannot be evicted; that is the cost you are controlling.
2. **Process in waves, checkpoint to a file.** Run ~6 cards at a time (one subagent each). After each wave, append the compact verdicts to a scratchpad file (the session scratchpad dir, e.g. `qa-triage-<board>.jsonl`) and drop them from working memory — the **file** is the accumulator, not the context. For columns over ~15 cards, or when you want a deterministic, resumable sweep, drive the fan-out with the **Workflow tool** (one pipeline item per card, `schema:` on the agent to force the compact return) instead of ad-hoc subagents.

Each per-card child returns ONLY this shape (≤~250 tokens — no prose essays, no pasted diffs/queries):
`{ card, class, cause_one_line, evidence_refs[], remedy, needs_human }`
`evidence_refs` are **pointers** (a SHA, a `file:line`, a row count, a rule filename) — not the content.

> Measure a sweep's cost with `submodules/skill-master/scripts/measure-skill-run.ts --cards N` (deno). Watch **parent peak context** — a healthy fan-out keeps it ~flat as the column grows; a leak grows it per-card until the run crashes.

## Phase 1 — Enumerate (lean work-list only)

1. Pull every card in the QA-Failed column **via the per-column endpoint** (`/boards/{B}/columns/{C}/cards.json` — `cards.json?board_id=` is silently ignored). **Paginate**: follow `Link: rel="next"` (page size escalates 15→30→50; don't stop on the first <15 page) and assert fetched count == `X-Total-Count`. A single fetch silently truncates. Full rules: "Reading a Board — AUTHORITATIVE" in `/fizzy`.
2. Build a **lean work-list** — one row per card with only `{card_number, title, assignee, latest_verdict_line}`, where `latest_verdict_line` is the first sentence of the most-recent `⛔/❌` comment (grep it out; don't pull the thread). **Do not** read full descriptions or full comment histories here — that is the per-card child's job (Phase 2), in a disposable context. Pulling them into this context for every card is the #1 cause of a sweep dying mid-column (see Batch discipline).
3. Print the work-list and pause for the user's go-ahead before triaging.

> The full description + end-to-end comment history (who reviewed, what passed before, when it last passed — a card that PASSED in May and re-failed in June is almost never a fresh regression, suspect class 2/3) still matter — but they are read **inside each card's subagent**, not here.

## Phase 2 — Triage each card in its own subagent

Fan out per **Batch discipline** above: one subagent per card (waves of ~6, or the Workflow tool for big columns). Hand each child only its `card_number` + the class definitions and checks below; it fetches its own card body + comments + ground truth in a disposable context and returns the compact verdict. The parent never sees the raw text.

**Step 2a — Classify** (inside the child). Fetch the card's full description and every comment (paginate, `Link: rel="next"`), read the history end-to-end, then assign a provisional class (1-6 above). Tells:
- "Files don't exist on staging" / "not merged" but GitHub says MERGED → class 1 or 4 (verify which).
- "Environment issue" / "price ID invalid" / "candidate linkage" → class 2.
- "Regression: <blocking behavior>" on a billing/unlock/cost action → class 3 (check the rules).
- "Migrations unapplied" / "edge fn not deployed" / a real `42883`/`23514`/null-field bug → class 2 (deploy) or 5 (code).
- "Spike / validate / no PR in the card" → class 6.

## Phase 3 — Verify the classification (this is the product)

**Step 2b — Verify** (same child as 2a). The provisional class is a hypothesis. Confirm or refute it with ground truth **before** routing. Run only the checks relevant to the provisional class. Fan-out across cards is handled by **Batch discipline** — never run these checks serially in the parent. The child then returns its compact verdict (`{card, class, cause_one_line, evidence_refs[], remedy, needs_human}`); keep raw git / DB / edge-fn output **out** of the return — cite a SHA, a row count, a `file:line`, a rule filename, not the dump.

- **Class 1/4 (stale-checkout vs dropped-merge):**
  - `gh pr view <n> --json state,mergeCommit` → get the merge commit SHA.
  - `git fetch origin <integration-branch>` then `git merge-base --is-ancestor <sha> origin/<branch>; echo $?` (0 = present in ancestry = **class 1, false-fail**; non-zero = **class 4, dropped**).
  - Then verify the *actual change* at HEAD (`git show origin/<branch>:<file>`), not just the SHA. Watch for shapes that *look* wrong but aren't (a deeply-nested prop path like `x.x.x.id`; a file left on disk but with zero importers).
- **Class 2 (live-in-prod / deploy / env):**
  - Is it already live? `git merge-base --is-ancestor <main-merge-sha> origin/main`. For DB, query prod (`source .env.local`, service-role PostgREST or Supabase MCP `execute_sql`) for the actual function body / row counts.
  - Migrations applied? `schema_migrations` for the versions. Edge fns deployed? Supabase MCP `list_edge_functions` / `get_edge_function` (and check `entrypoint_path` isn't a dev laptop).
  - "Invalid price ID" etc. → is it hardcoded live-mode config that only fails in a test-mode/staging context? If so it's staging env drift, not a code bug.
- **Class 3 (rule-misread):** Find the actual flow in source and check it against the project rules. A blocking modal on profile-unlock / billing is *correct* per `soft-gate-ui-hard-gate-wallet.md` (wallet ops hard-gate). Cite the rule.
- **Class 5 (genuine bug):** Reproduce it. For a plpgsql/CHECK/RPC failure, run an impact-analysis pass over every reader/writer of the affected column/symbol — the reported bug is often not the only one (a `pending_claim` CHECK gap hid behind a `has_permission` arity bug, both missed by 3 review rounds). Note that plpgsql bodies apply clean and fail at *runtime* — "the migration applied" is not "it works."
- **Class 6 (spike):** Confirm there's no PR and the deliverable was never produced. The remedy is to run the task or decide priority — not review.

## Phase 4 — Route to the remedy

| Class | Remedy | Eng cost |
|------|--------|----------|
| 1 Stale checkout | Annotate the card with the ground-truth proof + the look-wrong-but-right gotchas; ask the QA tester to `git fetch` and re-test current HEAD; re-queue to QA. | ~0 |
| 2 Live/deploy/env | If live in prod → "verify on prod and close." If deploy gap → prep the apply/deploy sequence (migration-first, then edge fns; both halves together). If env drift → fix staging config or route that QA to prod. | low |
| 3 Rule-misread | Annotate with the rule citation; re-queue. The behavior is correct. | ~0 |
| 4 Dropped merge | Quantify the damage first, then re-merge onto current HEAD. Flag the force-push source. | low–med |
| 5 Genuine bug | Cut a worktree off the integration branch, fix, open a PR, re-review, QA. The only class that needs real engineering. | real |
| 6 Spike | Surface the product-priority decision to the owner; run the task or archive. Not yours to decide. | n/a |

## Phase 5 — Report + act

- Produce a **plain-English report** from the checkpointed verdicts: per-card class + real cause + remedy + who/what's needed, then the systemic patterns (the pipeline leaks that produced the false-fails — stale-checkout QA, staging env parity, rule literacy, deploy-at-handoff).
- **Shared-state actions need authorization.** Posting verdicts to Fizzy, moving cards, merging, applying migrations, deploying — confirm with the user before the first one (then it's authorized for the rest of the session). Don't close cards yourself unless told; "verify on prod and close" still needs the prod verification to actually happen.
- Fizzy comments: HTML, attribute as a senior review, lead with the verdict (false-fail / correct-by-rule / real bug + PR). Don't re-assign an already-assigned person (the assignment API toggles → would unassign).

## Anti-patterns

- ❌ Running `/pr-review` on every QA-Failed card. Most aren't code-review problems.
- ❌ Trusting the QA verdict's framing without ground-truth verification.
- ❌ Pattern-matching a known failure mode (e.g. "Lovable dropped the merge") without proving it — check the merge-base ancestry first.
- ❌ Calling a plant "fixed" because the migration applies — plpgsql/CHECK bugs fail at runtime.
- ❌ Concluding from one reported bug — impact-analyze the surface; a second blocker often hides behind the first.
- ❌ Moving/closing cards or applying migrations to prod without the user's go-ahead.

## Board Reference

Used by Inputs to resolve the board + QA-Failed column per repo. Match by repo directory basename. When a board's QA-Failed column ID is missing, look it up by name (snippet in Inputs) and backfill this table.

| Repo directory name | Board | Board ID | QA-Failed Column ID |
|---|---|---|---|
| `vettedai-audition-supabase-version` | Vetted | `03faozjl3gdngcoyzpkr4vf87` | `03frpj9rn7vrewpk1y6rtcoj8` |
| `vetted-congrats-Flow-GENEROUS` | Congrats | `03f58rc5c48jorujpxqp5da5b` | *(lookup by name on first run)* |
| `backend-restructing` | Congrats (shared) | `03f58rc5c48jorujpxqp5da5b` | *(lookup by name on first run)* |

If no row matches: ask the user which board, then list its columns to find the QA-Failed one.

---

## Related
- `/pr-review` — the right tool for class 5 once you've cut the fix PR (and for genuinely re-reviewing a single PR). One branch of this skill, not the whole thing.
- `/impact-analysis` — use it in Phase 3 for any class-5 migration/CHECK/domain change.
- `/qa-handoff`, `/merge-to-prod` — the downstream steps once a card is genuinely cleared.
- Rules leaned on: `soft-gate-ui-hard-gate-wallet.md`, `committed-not-deployed-edge-fn.md`, `project_lovable_staging_rewrite_drops_prs`, `migration-and-writer-deploy-atomically.md`, `migration-impact-analysis-writers.md`, `fizzy-api-patterns.md`.
