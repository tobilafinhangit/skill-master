---
name: loose-ends
description: Sweep a work session for loose ends — findings, debt, follow-ups, and half-decisions that surfaced but were never filed anywhere durable — then VERIFY each is still real before filing the survivors to Fizzy as cards. Use deliberately before closing out a heavy session, or when the user says "any loose ends", "sweep for loose ends", "what did we leave open", "wrap up the session", "did we forget anything". A verification pass, not just a dump — most "loose ends" from a long session are already resolved by the time you look.
version: 1.0.0
license: MIT
metadata:
  author: VettedAI
  category: engineering-management
---

# Loose Ends

Sweep the current session for things that surfaced but never reached a durable home, **verify each is still real**, and file the survivors to Fizzy so a future session has the context instead of a human's memory.

## The one rule that earns its keep

**Verify before you file. Most loose ends from a long session are already dead.**

This is not a formality. In the session this skill was born from, a triage of four deferred items found **two were already fixed by the time they were written down**, and a third was stale. Filing them unverified would have created cards for work that was already done — board-decay, which is *worse* than prose-decay because a card looks authoritative. The sweep's value is the verification, not the dump. A skill that files everything it sees is a noise machine.

## When NOT to file (the bar)

File a loose end **only if** a future person would waste real time rediscovering it, **or** it would stay invisible until it bites. That's the bar. Everything below it is noise on a board that already has hundreds of cards.

- ✅ **File:** a deploy gap, an unshipped remainder of a partial PR, a bug found adjacent to the work, a decision deferred with real consequences, debt that will silently re-break (a `GRANDFATHERED` list that "must not grow" with nothing enforcing it).
- ❌ **Don't file:** "this function is a bit long", a preference, anything already covered by an open card, anything you *just fixed this session*, a thing that only mattered to this conversation.

If you're unsure whether something clears the bar, it probably doesn't — but surface it to the user in the summary rather than filing it silently. Let them promote it.

## Phase 1 — Gather candidates (read-only)

Scan the session for anything that surfaced and was **not** made durable. Durable = landed in a card, a CI check, a `.claude/rules/` file, or shipped code. NOT durable = a sentence in your own summary, a "worth remembering…", a "we should probably…", a deferred decision, a TODO you spoke but never wrote.

Signals to look for in the transcript:
- "worth remembering" / "note that" / "we should" / "someone should" / "follow-up" / "out of scope" / "separate issue" / "flag for later" / "TODO" — **the phrase "worth remembering…" is itself the signal to go make it structural.**
- A partial PR that shipped some ACs — the rest are loose ends unless carved into cards (see `epic-card-partial-pr-close`).
- A bug or gap found *adjacent* to the main task and set aside.
- A decision you presented as "your call" that never got a home.
- A guard/rule/list with a stated invariant that nothing enforces.

List them plainly. Don't file yet.

## Phase 2 — Verify each candidate against ground truth (the load-bearing phase)

For **every** candidate, answer: *is this still real, right now?* Do not trust the summary that produced it — the summary is what decayed. Check the world:

- **Already fixed?** Look at the live state, not the memory. A deploy gap → query the live catalog / hit the endpoint. A code smell → re-read the file on the integration tip. A "not applied" migration → check the ledger AND the catalog (per `schema-migrations-ledger-not-source-of-truth`). Something shipped between when it was noticed and now happens constantly.
- **Already filed?** Search the board before creating (Phase 3 covers the how). A duplicate card is worse than no card.
- **Owned elsewhere?** A CI check, a rule, an existing ticket may already carry it.

Classify each: **REAL & unfiled** (→ file), **already resolved** (→ drop, note it), **already filed** (→ drop, link it), **below the bar** (→ surface to user, don't file).

Report the classification to the user *before* filing anything.

## Phase 3 — File the survivors (MUTATES — get sign-off first)

**Never file without showing the user the list first.** They may kill some, reword others, or promote a below-the-bar item.

Use **`fizzy-file-card`** — it is the only path that verifies the card actually landed instead of floating into the invisible "Maybe?" lane (`column == null`, on no board — the trap that lost cards #2128/#2161). It ships with this same submodule:

```bash
# Put it on PATH once (per machine):
ln -sf "$PWD/submodules/skill-master/scripts/fizzy-file-card" ~/.local/bin/

# Discover columns, then file — the helper creates → triages → asserts column != null,
# and EXITS NON-ZERO if the card floats. A 201 is not success.
fizzy-file-card --list-columns --board {BOARD_ID}
fizzy-file-card --board {BOARD_ID} --column {COLUMN_ID} \
  --title "🟡 <concise, legible-without-opening title>" \
  --description-file /tmp/card-body.html
```

Card bodies are **HTML, not markdown**. Write enough context that a future session needs no memory of this conversation: what it is, the evidence (files, SHAs, live-state findings), why it matters, and what "done" looks like. See the `fizzy` skill for the full API contract.

Default landing column is the board's grooming/triage lane unless the item is urgent — a raw loose end is not yet groomed, so don't drop it straight into a priority lane. Boards:

| Board | ID |
|-------|-----|
| Bugs | `03fl735hqcd0h1pettl8o94oo` |
| Product | `03feaz5rc2t60wkn2rvjkhy6b` |
| Congrats | `03f58rc5c48jorujpxqp5da5b` |
| Vetted | `03faozjl3gdngcoyzpkr4vf87` |

## Output to the user

A short table: candidate → verdict (REAL / resolved / already-filed / below-bar) → action taken (card # + URL, or why not). Lead with what got filed. Name what you verified as *resolved* — that's proof the sweep did its job, not that it found nothing.

## Why this is a deliberate command, not an automated hook

This runs when **you** invoke it, at a natural breakpoint — not on a timer. A scheduled end-of-session pass fires at the wrong moment: the evidence has already decayed from context, so it would file vague cards from a faded memory, which is the exact prose-decay this exists to prevent. Run it while the session's context is still warm. File loose ends at the moment of discovery when you can (that keeps the evidence sharp); use this sweep as the deliberate safety net before closing a heavy session, where its real job is **verifying** the day's findings before they become cards.

## Related

- `fizzy` — the API contract + the `fizzy-file-card` helper this skill files with.
- `epic-card-partial-pr-close` — a partial PR's unshipped ACs are loose ends; carve them into cards, don't narrate them.
- `board-cleanup` — the board-side counterpart: this skill files *into* the board from a session; board-cleanup triages what's *already on* it.
- `schema-migrations-ledger-not-source-of-truth` — when verifying "is this applied?", check the catalog, not the ledger.
