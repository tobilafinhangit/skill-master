# Release epic gate policy

Shared policy for every workflow that decides what ships to production:
`merge-to-prod` (Phase 3.6) and `selective-staging-merge` (step 2). One copy of
the rules, two readers. Change the policy here, never inline in a skill.

**The question this answers:** a card can be QA-passed and sitting in Merge to
Prod while the rest of its epic — or other code already on staging — is not
approved. What ships, what is held, and what needs a human?

Two populations, one policy:

- **Epic siblings** — other cards in the same epic as a card being released,
  whether or not their code is on staging.
- **Riders** — changes in the release inventory (`BASE..HEAD`) whose card is
  NOT in the Merge-to-Prod column. A full promotion ships them whether or not
  anyone meant to.

## 0. Cardless patches ride

A change that maps to **no card at all** but came in through a **merged PR**
is a patch or quick fix (operator policy, 2026-10-03: these don't need cards
and are usually covered by another card). It **rides** — it does not block
`ready` and needs no card evidence. Record it as `cardless_patch: true` with
its `pr`, and list it in the release PR under **Cardless patches (riding)**.

- If it touches `supabase/migrations/`, billing/payment code, auth/RLS/grants,
  or an edge function's auth gate, mark it `sensitive: true` — it still rides;
  the flag just puts a ⚠ next to it in the PR list so a reviewer glances at it.
- A **direct commit with no PR and no card** is not a cardless patch: it needs
  evidence (standing infra: reconcile merge, deploy-lock record, CI/docs/rules),
  otherwise it stays `unreviewed` and blocks, as before.
- If a cardless PR's description names a card, it is not cardless — the card's
  column decides it via §3.

## 1. Finding siblings (epic membership)

Fizzy has no native epic, parent, or sub-task field. Resolve membership in this
order and record which source answered:

1. **Tag** — the card carries an `epic-<slug>` tag (applied by
   `grooming-architect` from 2026-10 onward). Siblings = every card with the
   same tag: resolve the id from `GET /tags.json` (title `epic-<slug>`), then
   `GET /cards.json?tag_ids[]=<TAG_ID>` (workspace-wide; the tag filter works,
   `board_id` is ignored — filter `board.name` client-side; paginate to
   exhaustion). Tagging is a toggle (`fizzy card tag`) — this gate only reads.
2. **Ticket folder** — a `.claude/tickets/<slug>/` folder whose `README.md` or
   `BUILD-PROMPTS.md` names the card (`#N`, `Fizzy card #N`, an `Order:` line).
   Siblings = every card number those files name. These folders are often
   untracked, so they exist only on the operator's machine — absence proves
   nothing.
3. **Description refs** — bare `#NNNN` references in the card description that
   resolve (via `GET /cards/<n>.json`) to cards on the same board. Weakest
   source: prose refs also point at related-but-separate work. Use them to
   nominate siblings, and say so in the report.

Nothing found → the card is **standalone**. Report it as
`epic: none found (tag/folder/refs checked)`. Standalone is a normal outcome,
not a failure.

## 2. Dependency (does the released card need the sibling?)

Read dependency only from explicit statements: a ticket folder's `Order:` line,
"X MUST merge before Y", "depends on #N", or the same wording on the card.
A card **depends on** a sibling only when such a statement says so.

No statement → **independent**. Do not infer dependency from shared files or
shared epic membership alone. If you have a concrete reason to suspect a
hidden dependency (the released card calls an RPC/table/route the sibling
introduces), surface it as `needs human` — never silently hold or ship.

## 3. Policy by the sibling's / rider's current column

Read the column live (`GET /cards/<n>.json` → `column.name`, `closed`) at audit
time. Never reuse a column from an earlier run.

| Column (Vetted board names) | Disposition | What the run does |
|---|---|---|
| Merge to Prod, or deliverable already an ancestor of the target | `ok` | Nothing extra. |
| Card closed (`closed: true`) | `ok` | Nothing extra. |
| **Manual UI/UX Testing** | `ship_with_note` | Ships. Listed in the PR under **Manual check pending**. Card stays in its column. |
| **Additional Admin Checks** | `ship_with_note` | Same as Manual UI/UX. |
| **QA to be confirmed** | `ask` | Present to the operator per card (what is pending, whether a released card depends on it). Operator chooses `ship_with_note` or `hold`. Never default silently. |
| **QA Failed** | `triage` | Classify with `qa-failed-triage`'s classes. Classes **1 stale checkout, 2 env/deploy, 3 rule-misread** → `ship_with_note` **only if** that verdict is written on the card as a comment (cite it). Classes **4 dropped merge, 5 genuine bug, 6 spike**, or no written verdict → `hold`. |
| In Progress, PR Open, any Priority column, Additional Grooming, Maybe? (no column) | `hold` | Not approved. |
| Any other / unrecognised column | `ask` | Unknown column name = human decision. |

For boards whose column names differ, map by meaning and print the mapping
before applying it.

## 4. Effect on the release

Apply per released card, then per rider:

- **Released card with a held sibling**
  - depends on it (§2) → the released card is also held. In `merge-to-prod`
    this makes it `not_ready` with reason `epic dependency #N held`.
  - independent → the released card ships; the PR lists the open sibling under
    **Epic siblings still open**.
- **Held sibling whose code is NOT on staging** → no release effect beyond the
  dependency rule above. Report it.
- **Held rider whose code IS on staging** → the run is `blocked (excluded work
  present)` and hands off to `selective-staging-merge`, with the held rider's
  units as the starting `--exclude`.
  - If selective cannot isolate it (mixed unit, conflict against target, empty
    replay), **stop** and put two options in writing to the operator:
    1. **Wait** — hold the promotion until the rider clears.
    2. **Ship full with recorded risk** — only on explicit operator choice.
       Post a risk comment on the rider's card (what ships, why, its QA state)
       **before** publishing the promotion.
- **`ship_with_note` riders** do not block `ready`. They count as reviewed
  change evidence of type `epic-gate:ship_with_note:<column>`.

## 5. Closure

Unchanged. A `ship_with_note` card is never closed by the release that carried
it. Its normal path continues: manual / admin pass → Merge to Prod → a later
run sees its deliverable already on target → offers closure with ancestry proof.

## 6. Report shape

Print one table (the parent context holds only this — card text stays in
subagents):

```
Epic gate (source: tag | folder | refs | none)
  released #A  epic <slug>  siblings: #B ok · #C ship_with_note(Manual UI/UX) · #D hold(QA Failed cls5; #A depends → #A held)
  rider    #E  QA to be confirmed → ASK
  rider    #F  Manual UI/UX → ship_with_note
```

Add to the PR's managed section (only sections that are non-empty):

```
### Manual check pending (ships now, card stays open)
- #C — Manual UI/UX Testing
### Epic siblings still open (not in this release)
- #D — QA Failed (held); #A independent of it
```

## Why

2026-10-03 grilling session. Releases hit two opposite failures. Too loose: a
Merge-to-Prod card shipped while a sibling it needed sat in QA Failed, with no
warning. Too strict: any rider blocked the run, even one only waiting on a
manual UI pass — which experience showed is safe to ship. The prior practice
lived in one repo rule (`promotion-pr-must-match-merge-to-prod-column.md`,
"triage the riders") that no skill read.
