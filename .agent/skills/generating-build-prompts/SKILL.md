---
name: generating-build-prompts
description: Use when a ticket set has been groomed and tech-reviewed (or is otherwise FINAL) and needs to be converted into copy-pasteable per-ticket build prompts for a fresh coding session. Generates a BUILD-PROMPTS.md alongside the ticket specs, with a chosen autonomous-vs-cautious ending applied consistently across the batch.
version: 1.0.0
license: MIT
---

# Generating Build Prompts

Turn a folder of FINAL tickets (already groomed + tech-reviewed) into a `BUILD-PROMPTS.md` — one fenced block per ticket, meant to be pasted verbatim into a fresh session to build that ticket end-to-end.

**Announce at start:** "I'm using the generating-build-prompts skill to write the build prompts."

## When to Use

- A ticket epic just finished grooming + tech-review and is ready to hand to engineering (self or otherwise)
- The user says "write the build prompts", "generate BUILD-PROMPTS", or references handing tickets off to a fresh session
- NOT for a single ad-hoc ticket with no epic folder — just write the prompt inline in that case

## Required Input

- The ticket folder under `.claude/tickets/<epic-slug>/` — must contain final per-ticket spec files (e.g. `A1-backend-thing.md`) and ideally a `README.md` epic overview
- If tickets aren't groomed + tech-reviewed yet, stop and say so — this skill formats final tickets, it does not groom them (use `grooming-architect` / `tech-review` first)

## Step 0 — Determine the spec source (once per invocation)

`.claude/tickets/` is untracked/gitignored in this repo — it exists only on the machine that ran grooming. Before writing any prompt, decide whether the assignee can read that path:

- **Assignee is you, in this same session/checkout** (or explicitly confirmed to have this exact local checkout) → local ticket files are a valid spec source. Cite `.claude/tickets/<epic-slug>/<ID>-<slug>.md` as usual.
- **Assignee is anyone else** (a bounty/remote engineer, a fresh session on a different machine, anyone whose access you have not explicitly confirmed) → **default to this branch.** Local files are NOT a valid spec source for them. The spec source must be **the Fizzy card itself** (description + comments) — see Step 3's "Spec:" line and Step 5's mandatory Fizzy-post step below.

When unsure which case applies, default to the remote case — citing a Fizzy card an assignee can't reach is invisible until they hit it; citing local files for yourself when a Fizzy card would've worked too costs nothing.

## Step 1 — Ask the mode (once per invocation, not per ticket)

Ask which ending every prompt in this batch gets. This is the one thing Tobi has been hand-editing at the end of every generated prompt — the skill exists to make it a deliberate choice instead of a manual override each time.

Use AskUserQuestion:

**Question:** "How far should each build prompt go before stopping?"
- **Autonomous (Recommended)** — build → PR → `/qa-handoff` → post a plain-English summary. No stop-and-wait for PR review. This is now Tobi's default mode.
- **Cautious** — stop after opening the PR and running `/pr-review`; wait for sign-off before QA handoff.

Don't ask per ticket. One answer governs the whole batch this invocation generates. If the user already stated the mode in their request ("autonomous", "all the way to QA", "stop at PR" etc.), skip the question.

## Step 2 — Determine build order

Read the epic's dependency graph (from the README or by reading each ticket's stated dependencies). State the order explicitly at the top of BUILD-PROMPTS.md, same as existing examples — e.g. "A1 MUST merge before A2 (A2 reads A1's marker)". Tickets with no dependency on each other may build in parallel; say so.

## Step 3 — Generate one fenced block per ticket

Follow the established house format exactly (verified against ~35 existing `BUILD-PROMPTS.md` files in this repo — do not deviate from this shape):

```
Build Fizzy card #<N> (ticket <ID>) end-to-end. The ticket is FINAL — groomed + tech-reviewed. Do NOT re-groom, re-plan, or re-review it.

Spec: <SPEC LINE — pick per Step 0>
  Local checkout (you, same session): .claude/tickets/<epic-slug>/<ID>-<slug>.md
    Epic overview: README.md in the same folder (open only if needed).
  Remote/bounty/unknown-access assignee (default): the Fizzy card #<N> description IS the spec — read it in
    full via the Fizzy API before starting. The tech-review comment on that same card has the full
    critique/impact-analysis writeup. (There is no local ticket file to read — the card is the only source
    of truth.)

Dependency: <None — build first | Ticket <X> (#<N>) MERGED first — reason>

Rules of engagement:
- The ticket is the plan (already tech-reviewed — do NOT re-review). Read that ONE spec source (per above) + the @-anchors it names. Nothing else up front.
- Token discipline: for any wider search spawn an Explore subagent on haiku and take only its summary. Never dump SQL result sets or whole migration files into context — the ticket already cites the exact functions/files.
- Work in a worktree off lovable-staging, set git identity BEFORE the first commit:
    git worktree add -b <ID>/<short-slug> .claude/worktrees/<short-slug> origin/lovable-staging
    git -C .claude/worktrees/<short-slug> config user.email "{WORKTREE_GIT_EMAIL}"
    git -C .claude/worktrees/<short-slug> config user.name  "{WORKTREE_GIT_NAME}"
- Follow red/green (test-driven-development skill): <the specific failing assertion(s) to prove first, drawn from the ticket's Verification section>.
- Hard constraint: <the ticket's explicit "do NOT touch" / banned-pattern list — pull verbatim from the ticket, don't paraphrase>.
- The real work: <2-4 sentences summarizing the actual implementation shape, pulling any "mirror existing pattern at <file:line>" anchors from the ticket verbatim>.
- Migration caveat (if the ticket touches the DB): new migration via CREATE OR REPLACE (never edit an applied one), Dashboard SQL editor to deploy, ends with the schema_migrations registry insert.
- Definition of Done = the ticket's Verification section. Also run: <the ticket's stated verification commands, e.g. npx tsc -p tsconfig.app.json --noEmit, scripts/audit-rbac-drift.ts>.
- <ENDING — see Step 1 mode, exact wording below>

Run this on Sonnet. /clear before <next ticket ID>.
```

### Ending text by mode

**Cautious** (the prior default — use only if explicitly chosen):
```
- When green: open a PR to lovable-staging, then run /pr-review against card #<N>. Stop and report — I handle QA/merge. Do NOT start <next ticket ID>.
```

**Autonomous** (current default):
```
- When green: open a PR to lovable-staging, then run /pr-review against card #<N>. If all goes well, run /qa-handoff and post a plain English summary.
```

Use the exact autonomous wording above (Tobi's own phrasing) — do not embellish or add extra caveats to it. If a specific ticket in the batch is genuinely higher-risk (touches billing, auth, a live-customer data write, an irreversible migration, or anything covered by `no-real-user-testing.md` / `no-destructive-db-commands.md`), flag that ticket to the user explicitly and ask whether it should be the cautious ending instead — don't silently downgrade it, and don't silently apply autonomous either. This is the one legitimate case for per-ticket override within an otherwise-autonomous batch.

## Step 4 — Keep blocks lean

Each block should be dense, not exhaustive — it's a prompt, not the ticket itself. Cite the spec file rather than restating its contents; pull only the load-bearing constraints (dependencies, hard "don't touch" lines, the DoD) into the prompt. If a ticket has no DB migration, omit the migration caveat line rather than including it as N/A.

## Step 5 — Write the file, post to Fizzy if remote, and confirm

Always write `.claude/tickets/<epic-slug>/BUILD-PROMPTS.md` (useful as your own reference/history regardless of assignee). Open with a one-line header stating the paste-into-fresh-session convention and the build order, matching:

```markdown
# BUILD-PROMPTS — <Epic Name>

Paste one block into a **fresh session** to build that ticket end-to-end. `/clear` between tickets. One ticket = one session = one PR.

**Order:** <dependency order>

Each block is deliberately lean. This epic was tech-reviewed — see TECH-REVIEW.md (if present).
```

**If Step 0 determined the remote/bounty/unknown-access case for any ticket, the local file is NOT sufficient — the build prompt for that ticket MUST also be posted as a comment on its Fizzy card**, wrapped in `<pre>` so it renders copy-pasteable:

```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0" \
  -H "Content-Type: application/json" \
  -d '{"comment": {"body": "<h2>Build Prompt</h2><p>Paste the block below into a fresh session to build this ticket end-to-end. Everything it needs is on this card (description + tech-review comment) — no local files required.</p><pre>...the prompt block...</pre>"}}'
```

This is not optional for a remote assignee — a `BUILD-PROMPTS.md` sitting only on the machine that ran grooming is invisible to them. Do this per-ticket immediately after writing that ticket's block, not as an afterthought at the end of the batch.

**Self-containment check (mandatory for any card with a remote/unknown-access assignee) before reporting the batch done:** fetch the card's description AND all its comments via the Fizzy API and grep for `.claude/` — any hit is a broken pointer for that assignee and must be fixed before moving on.

```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}.json" -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0" \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('description',''))" | grep -n "\.claude/"
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}/comments.json" -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0" \
  | python3 -c "import json,sys; [print(c.get('body',{}).get('plain_text','')) for c in json.load(sys.stdin)]" | grep -n "\.claude/"
# Expected: no output for a remote-assignee card. Any hit → fix before reporting done.
```

Report back which mode was applied to the batch, which spec-source branch (local vs Fizzy-card) applied to each ticket and why, whether the build prompt was posted to Fizzy, and call out any ticket flagged for the opposite ending per Step 3.

## Related

- `grooming-architect` — produces the tickets this skill formats; run first if tickets aren't final
- `tech-review` — pressure-tests the plan before this skill runs
- `pr-review` — what every generated prompt runs before either ending
- `qa-handoff` — what the autonomous ending chains into
