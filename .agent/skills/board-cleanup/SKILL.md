---
name: board-cleanup
description: Map a Fizzy board into a clear state-of-play, surface the real chaos (floating cards, stale artifacts, duplicate/overloaded work, dependency chains, scope-stale epics), then triage and split with the user's sign-off. Use when the user wants to "get back up to speed", "map out the board", "clean up Fizzy", reduce board chaos, or plan who-owns-what for a sprint/weekend. Repo-agnostic — works on any repo with a corresponding Fizzy board.
version: 1.0.0
license: MIT
metadata:
  author: VettedAI
  category: engineering-management
---

# Board Cleanup

Turn a chaotic Fizzy board into a clear map + an executable plan. This is the companion to the `fizzy` skill (which is the low-level API client) — this skill is the *workflow* on top of it.

The job is five phases: **Pull → Map → Flag → Triage → Scope-and-split.** Phases 1–3 are read-only. Phases 4–5 mutate the board — **never mutate without explicit user sign-off**, and prefer to do the safe parts (close artifacts, move floaters) before the judgment parts (owners, splits).

## The one rule that earns its keep

> **Verify against the live tree, never the card.** Cards go stale the moment they're written. Before you act on any claim ("17 fns left to clean", "table missing from staging", "not started"), check ground truth: the actual git branches, the deployed code, `to_regclass`/`information_schema`, the real file. In practice this routinely shrinks "epics" to near-done — and occasionally reveals the prod side is *cleaner* than the repo. This single check is what makes the plan trustworthy.

Apply it hardest in Phase 5, but keep it in mind throughout.

## Setup

```bash
# Token lives in the repo's env file, NOT the shell. User-Agent is mandatory (401 without it).
# Path varies by repo — Congrats: congrats/.env.local. Else: grep the tree for FIZZY_API_TOKEN
# (try ./.env.local, ./congrats/.env.local) or check the repo's own `fizzy` skill.
ENVFILE=$(ls congrats/.env.local .env.local 2>/dev/null | head -1)
TOKEN=$(grep -E '^FIZZY_API_TOKEN=' "$ENVFILE" | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
H=( -H "Authorization: Bearer $TOKEN" -H "User-Agent: VettedAI/1.0" )
```

**Pick the board for this repo.** Boards (account `6102589`):

| Board | ID | Repo it maps to |
|-------|----|-----------------|
| Congrats (Candidate-Facing) \| Engineering | `03f58rc5c48jorujpxqp5da5b` | vetted-congrats |
| Vetted (Recruiter-Facing) \| Engineering | `03faozjl3gdngcoyzpkr4vf87` | vettedai-audition |
| Bugs 🐛 | `03fl735hqcd0h1pettl8o94oo` | cross-repo |
| Feature Grooming \| Product Team | `03feaz5rc2t60wkn2rvjkhy6b` | product |

If the repo isn't obvious, ask the user which board.

## Phase 1 — Pull (read-only)

```bash
BOARD="<board-id>"
# Columns (IDs differ per board — never hardcode across boards):
curl -s "https://app.fizzy.do/6102589/boards/$BOARD/columns.json" "${H[@]}"
```

Pull every card, paginated. **CRITICAL GOTCHA:** `cards.json?board_id=X` requires the `.json` suffix AND **the `board_id` filter is silently ignored** — the endpoint returns cards from *all* boards. You MUST filter client-side by **EXACT** `board.name` equality — **never `startswith`**: sibling boards share a prefix (e.g. `Vetted (Recruiter-Facing) | Engineering`, `Vetted Onboarding Tool`, and `VettedAI GTM` all start with `Vetted`, so `startswith('Vetted')` silently conflates all three and inflates every count). Page size **escalates** (15→30→50…), so paginate by following `Link: rel="next"` — never stop on the first <15 page. (Full rules: "Reading a Board — AUTHORITATIVE" in `/fizzy`.)

```bash
url="https://app.fizzy.do/6102589/cards.json?page=1"; > /tmp/bc_cards.jsonl
while [ -n "$url" ]; do
  body=$(curl -s "$url" "${H[@]}" -D /tmp/bc_h.txt)
  echo "$body" | python3 -c "import sys,json;[print(json.dumps(c)) for c in json.load(sys.stdin)]" >> /tmp/bc_cards.jsonl
  url=$(grep -i '^link:' /tmp/bc_h.txt | sed -n 's/.*<\([^>]*\)>; *rel="next".*/\1/p')
done
# Then: rows = [c for c in jsonl if c['board']['name'] == '<exact BoardName>' and not c['closed']]
#   EXACT == only. startswith() conflates sibling "Vetted *" boards — verify your count by also
#   printing the distinct board names you matched, before trusting any total.
```

Useful fields per card: `number`, `title`, `closed`, `postponed`, `column` (`null` = floating/"Maybe" pile), `assignees[].name`, `tags`, `description_html`. Single-card detail needs `.json` too: `/cards/{n}.json`.

> **Blind spots — the walk only returns OPEN, non-postponed cards.** The **Not Now** (`postponed`) and **Done** (`closed`) lifecycle lanes are NOT returned by *any* list endpoint, so your map covers every active/floating card but is blind to those two — only the Fizzy UI shows their counts (often large: e.g. Congrats Not Now = 38, Done = 99+). Say so explicitly in the map rather than implying the board is empty there. The `not c['closed']` filter above is just belt-and-suspenders; closed cards never appear anyway. Also note boards auto-postpone idle cards (`auto_postpone_period_in_days`, ~30d) into Not Now — a long-idle card that vanished from a column was likely postponed, not shipped.

## Phase 2 — Map

Group open cards by column in pipeline order. Produce a tight table (column → count → card #s). Then re-cluster the *same* cards by **theme** (security, a refactor chain, a feature epic, etc.) — themes cut across columns and are where the real story lives.

## Phase 3 — Flag the chaos

Hunt for these specific smells (don't just say "it's messy"):

- **Floating cards** — `column == null`. The untriaged pile. List them; they're invisible work.
- **Stale artifacts** — auto-generated cards that aren't work (e.g. `Release Notes — <date>` from `/generating-release-notes`). Candidates to close. Watch for **duplicates** (same date / superset).
- **Overloaded owner** — one assignee holding many open PRs, especially a *sequential dependency chain* all open at once (nothing merges → everything stalls).
- **Dependency chains** — cards that must land in order (read `description_html` to confirm: "depends on #X", "blocks #Y", "paired with").
- **Scope-stale epics** — one card hiding 3+ workstreams across repos. Flag for Phase 5 splitting.
- **Cross-repo / paired cards** — work that has a sibling on another board.

## Phase 4 — Triage (MUTATES — get sign-off)

Present the plan, then execute the **safe parts first**:

1. **Close artifacts** — `POST /cards/{n}/closure.json` (note: `closure.json`, returns 204; plain `closure` 401s).
2. **Move floaters into priority columns** — `POST /cards/{n}/triage.json` with `{"column_id":"..."}` (204). **Respect the priority emoji already in the title/body** (🔴/🟠/🟡); cards marked 🟢 with no green column go to the bottom of 🟡. Read the card body when the title has no emoji.
3. Leave **owner assignment and column promotion of real work** to the user — those are judgment calls, not hygiene.

Record decisions as comments so the board is self-documenting (see Phase 5 examples). Don't spam — one comment per real decision.

## Phase 5 — Scope-and-split (MUTATES — get sign-off)

For any epic flagged in Phase 3:

1. **Scope against reality** (the rule above). Pull each workstream's *actual* state — git branches, deployed code, the live catalog. Mark what's already done, what's confirmed open, what needs investigation. This is the highest-value step; it routinely halves the work.
2. **Split** the epic into child cards, one per coherent workstream / repo, each carrying enough to execute: file anchors with line numbers, the exact fns/files, constraints (integration branch, "don't clobber prod-only code"), and a crisp "Done when". Mirror the `grooming-architect` style (file anchors + logic constraints + verification).
3. **Link** children back on the parent via a comment; turn the parent into an umbrella. Keep the priority emoji in child titles (team convention).

### Fizzy write cheat-sheet (the gotchas that cost real time)

| Action | Endpoint / payload | Notes |
|---|---|---|
| Create card | `POST /boards/{BOARD}/cards` · `{"card":{"title":"...","description":"<html>"}}` | Card body field is **`description`**, must be **HTML**. Number comes back in the `Location` header. |
| Comment | `POST /cards/{n}/comments` · `{"comment":{"body":"<html>"}}` | Comment field is **`body`** (HTML). |
| Move column | `POST /cards/{n}/triage.json` · `{"column_id":"..."}` | 204. |
| Close | `POST /cards/{n}/closure.json` | 204. `.json` required. |
| Assign (toggle) | `POST /cards/{n}/assignments.json` · `{"assignee_id":"..."}` | Same id again unassigns. |

Build JSON payloads with `python3 -c "import json,sys;print(json.dumps(...))"` — never hand-interpolate HTML into `-d` (quoting will bite you).

## Output to the user

Lead with the board-as-pipeline table + the theme clusters, then the *specific* chaos (named cards), then a proposed plan: who owns what, which priorities depend on what, what to close/split. Be definite. Recommend a starting point. Then ask for sign-off before any mutation.

Communication: plain English, gloss every piece of jargon the first time, concrete-before-abstract. The user may be non-engineer — the value is clarity, not completeness.

## Related
- `fizzy` skill — the low-level API client this builds on.
- `grooming-architect` skill — the style for child-card descriptions in Phase 5.
- `merge-to-prod` / `qa-handoff` skills — natural follow-ons once the board is mapped.
