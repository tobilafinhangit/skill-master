---
name: ticket-review
description: Reviews Fizzy tickets with a senior eng + PM + designer panel, then posts critique and revised ticket as an HTML comment. Use when reviewing grooming tickets for technical accuracy before engineering picks them up.
version: 1.0.0
license: MIT
---

# Ticket Review

Review Fizzy tickets through a panel of a senior full-stack engineer, a product manager, and a product designer — then post the results back to the card.

**Announce at start:** "I'm using the ticket-review skill to review this ticket."

## Review Hygiene (read this first)

Every invocation begins with a fresh Fizzy API GET — never reuse drafts or analysis from a prior session.

- ❌ Do NOT read pre-existing files under `.claude/tickets/`, `.claude/notes/`, `/tmp/*review*`, or any path that looks like a previously-authored draft for this card. Even files matching the current card number are stale by definition — the source of truth is the live Fizzy API.
- ❌ Do NOT reuse a panel verdict, critique, or comment body that was generated for a different card earlier in this chat or a previous session. Posting #712's review on #740 is the canonical failure mode this rule prevents (Fizzy #794, May 2026).
- ✅ Always start from a live Fizzy API GET of the card + its comments (Step 1 below). Synthesize fresh.
- ✅ If you find an existing draft file matching the current card, surface it to the user as a warning ("there's a draft at `.claude/tickets/<x>.md` from an earlier session — ignoring it; ask if you'd like me to delete it") but do not read or reuse it.

## When to Use

- When reviewing tickets from PMs or designers for technical accuracy
- When the user says "review ticket", "review card", "critique this ticket"
- Before engineering picks up grooming tickets

## Input Formats

### Single card
```
/ticket-review 337
/ticket-review 337 --board bugs
```

### Batch (max 3 cards)
```
/ticket-review 337 338 339
/ticket-review --column "Additional Grooming" --board product
```

If no `--board` is specified, default to the **Product board** (`03feaz5rc2t60wkn2rvjkhy6b`).

If `--column` is used, fetch all cards in that column but **cap at 3 cards**. If the column has more than 3, list all card titles and ask the user which 3 to review.

## Board Reference

| Board | Board ID |
|-------|----------|
| Product | `03feaz5rc2t60wkn2rvjkhy6b` |
| Bugs | `03fl735hqcd0h1pettl8o94oo` |
| Vetted | `03faozjl3gdngcoyzpkr4vf87` |
| Congrats | `03f58rc5c48jorujpxqp5da5b` |

## Workflow

### Step 1: Fetch Card Details + Comments

```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null

# Get card details
CARD_JSON=$(curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json")

# Get all comments on the card
COMMENTS_JSON=$(curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json")
```

Extract from card JSON:
- `title` — the ticket title
- `description` (HTML body) — the ticket content
- `column.name` — current column
- `board.id` — which board it's on
- `creator.name` — who wrote the ticket
- `assignees` — who's assigned

Extract from comments JSON:
- Each comment's `body` (HTML) and `creator.name`
- Combine into full ticket context for the review panel

**Display to user:** "Reviewing card #{NUMBER}: {title}"

### Step 2: Run the Review Panel (Use Subagents)

The review is performed by a panel of three personas. Spin up subagents for parallelism where possible.

#### Step 2a: Critique (Subagent)

Prompt the subagent with the full card context (title + body + comments) and instruct it:

> You are a review panel comprised of a senior full-stack engineer, a product manager, and a product designer who know this codebase and product deeply and have shipped similar features to production.
>
> Your job is NOT to change the goal — only to pressure-test the approach.
>
> **Critique this ticket.** Be specific and direct:
> - What are the technical risks or incorrect assumptions?
> - Are there inefficiencies in the proposed approach?
> - Are there better paths the author may not have considered?
> - Does the ticket have enough context for an engineer to execute without guessing?
> - Are there missing edge cases, error handling, or rollback plans?
>
> Structure your critique by persona:
> - **Senior Engineer:** Technical accuracy, architecture, anti-patterns
> - **Product Manager:** Scope clarity, user impact, prioritization
> - **Product Designer:** UX implications, user flow gaps, accessibility

The subagent should have access to the codebase (Grep, Glob, Read) so it can verify technical claims in the ticket against actual code.

#### Step 2b: Revised Ticket (Subagent — depends on 2a)

After the critique is complete, prompt a second subagent with the original ticket + the critique:

> Based on the critique above, produce an improved version of this ticket.
>
> If the original is already optimal, state why explicitly — do not change it for the sake of changing it.
>
> The revised ticket should:
> - Keep the same goal/intent as the original
> - Fix any technical inaccuracies identified in the critique
> - Add missing context, edge cases, or guardrails
> - Be specific enough for an AI coding agent to execute without guessing
> - Include file anchors (@file references) where helpful
> - Include verification steps (Definition of Done)
>
> Format the revised ticket using the grooming-architect template:
> - Strategic Narrative (Debate → Pivot → Mechanism)
> - AI-Agent Instructions (Context Anchors, Logic Change, Technical Guardrails, Clue, Verification Steps)
> - Estimated Tier (S/M/L/XL based on verification step count)

#### Step 2c: Impact Analysis (Subagent — depends on 2b)

Run the **impact-analysis** skill on the final revised ticket. Use the Skill tool:

```
Skill: impact-analysis
```

Pass the revised ticket's proposed changes to the impact analysis. This identifies downstream risks before engineering starts.

#### Step 2d: PM Scope Change Summary (after 2b)

The ticket authors are PMs who are not technical. After generating the revised ticket, write a **plain-language scope change summary** that a non-technical PM can understand. This section answers the question: "How has the scope of this ticket changed from the original to the revised version, and why?"

Structure:
- **Original scope:** What the ticket described in plain language (no code references)
- **What we discovered:** What already exists or what the review revealed (explain in product terms, not code)
- **Revised scope:** What the ticket now covers, in numbered steps a PM can follow
- **What was removed/deferred:** What was cut and why (in business terms — e.g., "requires a 2-sprint dependency" not "needs a schema migration")
- **Why the change:** One paragraph explaining the reasoning in terms a PM cares about (risk, effort, dependencies, avoiding duplicate work)

**Guidelines:**
- Use zero code references — no function names, file paths, or technical jargon
- Frame everything in terms of user impact, effort, risk, and dependencies
- Be direct but respectful — the goal is to help the PM understand, not to critique their writing
- Address the PM by first name if known (from the card's `creator.name`)

### Step 3: Assemble and Post Comments

The review is posted as **two separate comments** on the card so the PM can read their summary without scrolling past engineering content. **Use HTML formatting** (Fizzy renders HTML, not Markdown).

**Order matters:** post the engineering comment FIRST, then the PM summary SECOND. Fizzy displays comments oldest-first, so the PM summary lands at the bottom where the PM expects to find a direct message addressed to them.

#### Comment 1 — Engineering Review (Critique + Revised Ticket + Impact Analysis)

```html
<h2>Ticket Review — Card #{NUMBER}</h2>
<p><em>Reviewed by: Senior Engineer + Product Manager + Product Designer panel</em></p>

<h3>1. Critique</h3>
<h4>Senior Engineer</h4>
<ul><li>...</li></ul>
<h4>Product Manager</h4>
<ul><li>...</li></ul>
<h4>Product Designer</h4>
<ul><li>...</li></ul>

<h3>2. Revised Ticket</h3>
<!-- Full revised ticket content here -->
<!-- Use <pre> for code blocks, <code> for inline code -->
<!-- Use <table> for structured data -->

<h3>3. Impact Analysis</h3>
<table>
<tr><th>Change</th><th>Risk Level</th><th>Affected Consumers</th></tr>
<tr><td>...</td><td>...</td><td>...</td></tr>
</table>

<hr>
<p><em>Generated by ticket-review skill — see follow-up comment for PM scope-change summary</em></p>
```

#### Comment 2 — PM Scope Change Summary (standalone, plain-language)

```html
<h3>Scope Change Summary for PM</h3>
<p>Hey {CREATOR_FIRST_NAME} — here is how and why the scope changed (standalone summary; full engineering critique is in the previous comment):</p>
<p><strong>Original scope:</strong> ...</p>
<p><strong>What we discovered:</strong> ...</p>
<p><strong>Revised scope:</strong> ...</p>
<p><strong>What was removed/deferred:</strong> ...</p>
<p><strong>Why the change:</strong> ...</p>

<hr>
<p><em>Generated by ticket-review skill</em></p>
```

#### Post the comments

```bash
# Comment 1 — engineering review
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  --data-binary @/tmp/comment_engineering.json
# 201 = success

# Comment 2 — PM scope change summary (post AFTER comment 1 succeeds)
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  --data-binary @/tmp/comment_pm_summary.json
# 201 = success
```

**Why two comments instead of one:** the PM summary is written for a non-technical reader. Burying it as section 4 of a long engineering comment forces the PM to scroll past critique and revised-ticket content that wasn't written for them. A standalone comment also makes it linkable / quotable on its own and reads as a direct message to the PM rather than an appendix.

### Step 4: Confirm to User

Report back:

```
Ticket Review Complete:
- Card #{NUMBER}: {title}
- Critique: {summary — e.g., "3 technical risks identified, 2 scope gaps"}
- Revised: {summary — e.g., "Added missing RLS policy step, corrected API endpoint"}
- Impact: {risk level — e.g., "Risk: Moderate (2 consumers affected)"}
- Comment posted to Fizzy card #{NUMBER}
```

For batch reviews, show a summary table:

```
| Card | Title | Risks | Impact | Comment |
|------|-------|-------|--------|---------|
| #337 | ...   | 3     | Moderate | Posted |
| #338 | ...   | 1     | Safe     | Posted |
```

## Batch Mode

When reviewing multiple cards:

1. **Cap at 3 cards per invocation.** If more are requested, ask the user to pick 3.
2. **Run reviews in parallel** — each card gets its own set of subagents.
3. **Post comments independently** — don't wait for all reviews to finish before posting.
4. If any card fails (API error, empty card body), skip it, report the error, and continue with the rest.

### Column-based batch

When `--column` is specified:
1. Fetch all cards on the board: `GET /cards?board_id={BOARD_ID}`
2. Filter to cards in the specified column (match `column.name` case-insensitively)
3. If more than 3 cards, display the list and ask the user to pick up to 3
4. Review the selected cards

## Fizzy API Reminders

- **Always use `.json` suffix** on action endpoints (comments, triage, assignments)
- **Token**: `source .env.local` or `source congrats/.env.local` -> `$FIZZY_API_TOKEN`
- **Account slug**: `6102589`
- **Comments endpoint**: `POST /cards/{NUMBER}/comments.json` with `{"comment": {"body": "..."}}`
- **Card details**: `GET /cards/{NUMBER}.json`
- **Card comments**: `GET /cards/{NUMBER}/comments.json`
- HTML in comments: use `<h2>`, `<h3>`, `<ul>/<li>`, `<table>`, `<code>`, `<pre>` — Fizzy renders HTML
- Checkboxes: use `☐` character (no `<input>` support)

## Error Handling

| Error | Action |
|-------|--------|
| 401 Unauthorized | Check `$FIZZY_API_TOKEN` — source `.env.local` |
| 404 Not Found | Card number doesn't exist — verify with user |
| Empty card body | Skip review, tell user "Card #{N} has no description" |
| Comment post fails | Show the review to the user in the terminal instead |

## Team Reference

| Person | Role | User ID |
|--------|------|---------|
| Elvis Muchiri | QA Lead | `03fcio1h8spstjpkc82vciugk` |
| Oussama | Backend | `03f5clrwhb0jpi7h8yxhzfc2i` |
| Tobi Lafinhan | Owner | `03f58r3y17c4p4ucpvaf7mn5g` |
