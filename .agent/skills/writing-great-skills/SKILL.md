---
name: writing-great-skills
description: Reference for writing, editing, and pruning skills and rules well — the vocabulary and failure modes that keep them lean and predictable.
disable-model-invocation: true
---

# Writing Great Skills

> **Note:** This skill references `.claude/rules/*.md` files from the original author's private repos — optional deep-dive context, not required. If those files aren't present in your repo, follow the inline instructions in this skill directly.

A skill (or a `.claude/rules/*.md` rule) exists to wrangle determinism out of a stochastic system. **Predictability** — the agent taking the same *process* every run — is the root virtue; every lever below serves it.

This is the *quality* reference. For scaffolding a new skill (folders, frontmatter, symlinks) use `/creating-skills`; for "do we already have a skill for X?" use `/skill-strategist`. This skill is what you hold those outputs — and the rules corpus — to.

Adapted from Matt Pocock's [writing-great-skills](https://github.com/mattpocock/skills).

## Invocation — who can reach it

Two choices, trading different costs:

- **Model-invoked** (default — omit `disable-model-invocation`): the agent can fire it autonomously *and* other skills can reach it. Costs **context load** — the description sits in the window every turn. Write a model-facing `description` with rich triggers ("Use when the user wants…, mentions…").
- **User-invoked** (`disable-model-invocation: true`): only the human typing the name reaches it; no other skill can. Zero context load, but it spends **cognitive load** — *you* are the index that has to remember it exists. The `description` becomes a human-facing one-line summary; strip the trigger list.

Pick model-invocation only when the agent must reach the skill on its own, or another skill must. If it only ever fires by hand, make it user-invoked and pay no context load. When user-invoked skills pile up past what you can remember, a **router skill** (here: `/skill-strategist`) cures the cognitive load.

## Information hierarchy

Material sits on a ladder ranked by how immediately the agent needs it:

1. **In-skill step** — an ordered action in `SKILL.md`. Each step ends on a **completion criterion**: the *checkable* condition that says the work is done. Make it exhaustive where it matters ("every modified writer accounted for", not "list some writers") — a vague criterion invites **premature completion**.
2. **In-skill reference** — a definition/rule/fact consulted on demand. Often a flat peer-set (every rule on one rung) — fine, not a smell.
3. **External reference** — pushed into a separate file, reached by a **context pointer**, loaded only when the pointer fires.

**Progressive disclosure** is the move down the ladder — out of `SKILL.md` into a linked file — so the top stays legible. The test is **branching**: inline what every run needs; push behind a pointer what only some runs reach. A pointer's *wording*, not its target, decides how reliably the agent follows it.

## Leading words

A **leading word** is a compact concept already in the model's pretraining that the agent thinks *with* while running the skill (e.g. *tight loop*, *red*, *seam*, *sediment*). It anchors a whole region of behaviour in the fewest tokens by recruiting priors the model already holds, and — when the same word lives in your prompts, docs, and code — makes the skill fire more reliably.

Hunt for restatements a leading word retires:

- "fast, deterministic, low-overhead" → a *tight* loop.
- "a failing signal you trust" → the loop goes *red*.

You win twice: fewer tokens *and* a sharper hook. Assume every skill carries restatements that leading words retire.

## Pruning — the discipline this skill exists for

Most of our skills and our 95-rule corpus were grown by accretion. Pruning is not optional maintenance; it is what keeps the always-loaded context affordable.

- **Single source of truth.** Each meaning lives in exactly one place, so changing the behaviour is a one-place edit. A fact repeated across two rules is **duplication**.
- **Relevance.** Does the line still bear on what the skill does? Stale incident-specifics that no longer guide behaviour are **sediment**.
- **No-op hunt — sentence by sentence.** Run the no-op test on each sentence in isolation: *does it change behaviour versus what the model already does by default?* If not, delete the whole sentence — don't trim words from it. Be aggressive; most prose that fails should go, not be rewritten.

## Failure modes — diagnose a skill or a rules corpus against these

- **Premature completion** — ending a step before it's genuinely done. Fix the completion criterion first (cheap); only if it's irreducibly fuzzy *and* you see the rush, split the step so later steps aren't in view.
- **Duplication** — the same meaning in more than one place. Costs maintenance and tokens, and inflates that meaning's apparent importance. (In our corpus: the same anti-pattern restated across sibling rules.)
- **Sediment** — stale layers that settle because adding feels safe and removing feels risky. The default fate of any corpus without a pruning discipline. **Our rules index is the textbook case.**
- **Sprawl** — simply too long, even when every line is live. The cure is the ladder: disclose reference behind pointers; split by branch.
- **No-op** — a line the model already obeys, so you pay load to say nothing. A weak leading word (*be thorough* when the agent already is) is a no-op; the fix is a stronger word, not more words.

## Applying this to `.claude/rules/`

Our rules are model-context every session, so the corpus pays context load like a giant always-loaded skill. Hold it to the same bar:

- A new rule from `/learning-from-corrections` earns its place only if it changes behaviour the model wouldn't already take, and isn't already covered by a sibling rule (link instead via `[[name]]`/relative link).
- Merge rules that share a root cause into one with sub-cases, rather than N near-duplicates.
- A rule whose incident is fully fixed by tooling (a deploy guard, an audit script) can often collapse to a one-line pointer to that tool — the long narrative is sediment once the guard exists.
- The CLAUDE.md index line is the rule's *description* — same rules apply: one trigger, no restatement of the body.
