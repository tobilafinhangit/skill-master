---
name: tech-review
description: Pressure-tests an implementation plan or technical approach through a senior full-stack engineer + senior tech lead panel — critique, revised plan, then impact analysis — and prints a clean final plan. Use when reviewing a plan after grooming-architect or ticket-review, mid-hotfix, or before building something new, and the user says "tech review", "pressure-test this plan", "review this approach", or "stress-test this plan".
version: 1.0.0
license: MIT
---

# Tech Review

> **Note:** This skill references `.claude/rules/*.md` files from the original author's private repos — optional deep-dive context, not required. If those files aren't present in your repo, follow the inline instructions in this skill directly.

Pressure-test a technical plan through a panel of a senior full-stack engineer and a senior tech lead who know this codebase and product deeply and have shipped something similar to production. **The job is not to change the goal — only to pressure-test the approach.**

**Announce at start:** "I'm using the tech-review skill to pressure-test this plan."

## When to Use

- After `grooming-architect` produces tickets, to validate the *implementation approach* before building
- After `ticket-review`, when the plan needs a second technical pass
- Mid-hotfix, to sanity-check a fix before shipping under pressure
- Before building something new, to stress-test the design
- When the user says "tech review", "pressure-test this plan", "review this approach", "stress-test this", "poke holes in this"

**Not for:** reviewing a Fizzy *ticket spec* (use `ticket-review`), reviewing an *open PR's code* (use `pr-review`), or debugging a live bug (use `troubleshooting`). This skill reviews a *plan/approach*, not shipped code.

## Input

The plan can come from three places — detect which:

1. **In-context** (default) — the plan is already in the conversation (something we just designed, a grooming output, a hotfix idea). Review it directly.
2. **A file path** — `/tech-review docs/plans/2026-06-10-foo.md`. Read the file first.
3. **A Fizzy card** — `/tech-review --card 1349` (optionally `--board <name>`). Fetch the card + comments via the Fizzy API (see "Optional: Fizzy" below) and treat its body as the plan.

If no plan is identifiable in any of these, ask the user to paste it or point at it. **Never invent a plan to review.**

## Workflow

Run the three steps in order. Steps 1 and 3 each benefit from a subagent; spin them up for parallelism and codebase grounding. Step 2 depends on Step 1.

### Step 1: Critique (Subagent)

Spin up a subagent with codebase access (Grep, Glob, Read) so it can verify claims against actual code, not vibes. Give it the full plan and this instruction:

> You are a panel of a senior full-stack engineer and a senior tech lead who know this codebase and product deeply and have shipped something similar to production. Your job is NOT to change the goal — only to pressure-test the approach.
>
> **Critique this plan.** Be specific and direct — cite real files, functions, and prior incidents where relevant:
> - **Risks** — what breaks, what's fragile, what assumptions are wrong, what's the blast radius?
> - **Inefficiencies** — wasted work, over-engineering, simpler paths, existing code being reinvented?
> - **Better paths** — approaches the author may not have considered, with the tradeoff named?
> - **Gaps** — missing edge cases, error handling, rollback/backout plan, auth/RLS story, migration safety, deploy/config drift?
> - **Codebase fit** — does this contradict an existing `.claude/rules/` rule or a known gotcha in this repo? Verify against the actual code.
>
> Ground every claim. If you assert "X already exists," show the file. If you assert "this will fail," name the mechanism. Flag anything you could not verify as an assumption, not a fact.

The subagent returns a structured critique. Surface its key findings to the user.

**Runtime-consumer gate (mandatory):** During critique, verify every new exported helper,
adapter, hook, state contract, or renderer guard has both a production consumer on the affected
user path and an integration/component/E2E test proving that usage. An abstraction with only unit
tests is a review finding unless the ticket explicitly says the work is scaffolding-only. Require
the revised plan to include `criterion → production path → test` traceability for every behavioral
acceptance criterion.

### Step 2: Revised Plan (depends on Step 1)

With the original plan + the critique, produce an improved version:

> Based on the critique, produce an improved version of this plan.
>
> **If the original is already optimal, say so explicitly and why** — do not change it for the sake of changing it. Partial: keep what's sound, fix what isn't.
>
> The revised plan must:
> - Keep the same goal/intent as the original
> - Resolve each material risk and gap the critique raised (or explicitly accept it with a reason)
> - Prefer the simpler/cheaper path when the tradeoff favors it
> - Be concrete enough for an AI coding agent to execute without guessing — file anchors (`@path`), exact functions, sequenced steps
> - Include a Definition of Done / verification steps
> - Call out any new migration, RLS, deploy, or config step the critique surfaced

### Step 3: Impact Analysis (on the revised plan)

Run the **impact-analysis** skill on the *revised* plan to map downstream blast radius before anyone writes code:

```
Skill: impact-analysis
```

Pass it the concrete changes the revised plan proposes (touched files, shared functions/hooks, schema/API/type changes). Fold its risk matrix into the final output.

### Step 4: Output a Clean Final Plan

Print one clean, self-contained final plan to the terminal — this is the deliverable. Structure:

```markdown
# Tech Review — <plan title>

## Verdict
<1–2 sentences: ship as-is / revise / rethink, and the single biggest risk>

## 1. Critique
**Senior Engineer:** <bullets>
**Tech Lead:** <bullets>

## 2. Revised Plan
<the improved, execution-ready plan — or "Original is optimal because…">

## 3. Impact Analysis
| Change | Risk | Affected consumers | Mitigation |
|--------|------|--------------------|------------|
| …      | 🟢/🟡/🔴 | … | … |

## Open Questions
<anything that needs a human decision before building>
```

Keep the final plan tight and skimmable — Tobi reads these to decide whether to build. Lead with the verdict.

## Optional: Post to Fizzy

If the user passed `--card <N>` (or asks to post the review back), post the **final plan** as an HTML comment on that card after Step 4. Fizzy renders HTML, not Markdown.

```bash
source .env.local 2>/dev/null || source congrats/.env.local 2>/dev/null

# Fetch card + comments to use as the plan source
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0"
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0"

# Post the final plan as a comment (field is "body", HTML content)
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0" \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/tech_review_comment.json
# 201 = success
```

Comment body shape:

```html
<h2>Tech Review — Card #{N}</h2>
<p><em>Senior Engineer + Tech Lead panel — pressure-tested the approach, not the goal.</em></p>
<h3>Verdict</h3><p>…</p>
<h3>1. Critique</h3><ul><li>…</li></ul>
<h3>2. Revised Plan</h3><!-- use <pre>/<code> for code, <table> for structure -->
<h3>3. Impact Analysis</h3><table>…</table>
<hr><p><em>Generated by tech-review skill</em></p>
```

**Board reference** (default to the board most relevant to the plan; ask if ambiguous):

| Board | ID |
|-------|-----|
| Product | `03feaz5rc2t60wkn2rvjkhy6b` |
| Bugs | `03fl735hqcd0h1pettl8o94oo` |
| Congrats | `03f58rc5c48jorujpxqp5da5b` |
| Vetted | `03faozjl3gdngcoyzpkr4vf87` |

Fizzy gotchas: `.json` suffix on every endpoint; **`User-Agent` header is mandatory** (401 without it); comment field is `body`, not `content`; lists paginate at ~15/page. Token lives in `congrats/.env.local` as `$FIZZY_API_TOKEN`. See the `fizzy` skill for full API patterns.

## Notes

- **Stay grounded.** The value of this skill is verified critique, not generic advice. A subagent that hasn't opened the code produces the same review for every plan — don't accept that.
- **Don't re-litigate the goal.** If the plan's objective seems wrong, flag it once in Open Questions and move on; the panel's job is the *approach*.
- **Chain position:** `grooming-architect` (make tickets) → `planning` (write the plan) → **tech-review** (pressure-test it) → `executing-plans` / build.
