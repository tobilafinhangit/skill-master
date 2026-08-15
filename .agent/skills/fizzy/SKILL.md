---
name: fizzy
description: Interact with Fizzy (37signals) project management boards via REST API. Use when the user wants to create, read, update, or close Fizzy cards, add comments, check board status, create new boards, or file bugs/features.
---

# Fizzy Project Management Integration

Interact with the team's Fizzy boards directly via the REST API using `curl` or `WebFetch`.

## Setup (do this once per org/repo)

Every `{FIZZY_ACCOUNT_ID}` placeholder in this skill (and in `board-cleanup`, `pr-review`,
`merge-to-prod`, `qa-handoff`, and the other Fizzy-aware skills) means the same thing: your
Fizzy/Basecamp account slug, the segment right after `app.fizzy.do/` in your board URLs
(e.g. `https://app.fizzy.do/1234567/boards/...` → account is `1234567`). Find yours by opening
any board in the browser and reading it out of the URL, or via `GET /my/identity`. Set it once
(env var, or just find-and-replace in your fork) rather than re-deriving it per skill.

The board names/IDs in the **Team Boards** table below, the `User-Agent: VettedAI/1.0` header,
and the `congrats/.env.tokens` path in Authentication are this skill's original examples —
replace them with your own board names/IDs, product name, and token file location.

## Authentication

All requests require a Bearer token. **It is NOT in the shell environment by default** — a bare
`echo $FIZZY_API_TOKEN` prints nothing. Read it from the repo's gitignored env file first:

```bash
# Example layout — adjust the path to wherever your repo keeps the token:
TOKEN=$(grep -E '^FIZZY_API_TOKEN=' .env.local | head -1 | cut -d= -f2- | tr -d "\"'" | tr -d '[:space:]')
```

**Two headers are mandatory on every request:**

| Header | Why |
|---|---|
| `Authorization: Bearer $TOKEN` | auth |
| `User-Agent: <your-product>/1.0` | **401 without it** — and the 401 looks exactly like a bad token |

> **NEVER hardcode the token.** Always read it from the env file.

## API Base URL

```
https://app.fizzy.do/{FIZZY_ACCOUNT_ID}
```

Account slug: `{FIZZY_ACCOUNT_ID}` — see **Setup** above.

## Team Boards

Example boards from this skill's original org — replace with your own board names and IDs.

| Board | Fizzy Name | Board ID | When to use |
|-------|-----------|----------|-------------|
| **Bugs** | Bugs 🐛 | `03fl735hqcd0h1pettl8o94oo` | `/fizzy bug`, support-reported issues, regressions |
| **Product** | Feature Grooming \| Product Team | `03feaz5rc2t60wkn2rvjkhy6b` | `/fizzy feature`, product ideas, enhancements |
| **Congrats** | Congrats (Candidate-Facing) \| Engineering | `03f58rc5c48jorujpxqp5da5b` | Congrats frontend issues |
| **Vetted** | Vetted (Recruiter-Facing) \| Engineering | `03faozjl3gdngcoyzpkr4vf87` | Vetted platform issues |

**Use these board IDs directly** when creating cards — no need to list boards first.

## Sub-Commands

### `/fizzy bug [description]`
Create a bug card on the Bugs board.

**Steps:**
1. Use the Bugs board ID from the table above (no need to list boards)
2. Pick the target column: `fizzy-file-card --list-columns --board 03fl735hqcd0h1pettl8o94oo`
3. File it with the helper — it creates, triages, **re-reads, and exits non-zero if the card
   is still floating** (see [Create Card](#create-card) for why that last step is mandatory):
   ```bash
   fizzy-file-card --board 03fl735hqcd0h1pettl8o94oo --column <col> \
     --title "..." --description-file body.html
   ```
   Filing by raw curl instead? You **must** create → triage → verify yourself.
4. Add the `bug` tag if available
5. Return the card URL

### `/fizzy feature [description]`
Create a feature card on the Product board. Same create → triage → **verify** requirement.

### `/fizzy status`
Show all open cards assigned to the current user across all boards.

**Steps:**
1. Get the user's identity: `GET /my/identity`
2. For each board, list cards filtering by assignee
3. Display a summary grouped by board

### `/fizzy close [card_number] [optional comment]`
Close a card and optionally add a completion comment.

**Steps:**
1. If comment provided: `POST /:slug/cards/:number/comments`
2. Close the card: `POST /:slug/cards/:number/closure`

### `/fizzy card [number]`
Show details for a specific card.

### `/fizzy board [name]`
Show a summary of a board's columns and card counts.

### `/fizzy create-board [name]`
Create a new board with the standard engineering column structure (matches Vetted/Congrats layout).

**Steps:**
1. Source the token: `source .env.local`
2. Create the board:
```bash
LOCATION=$(curl -s -D - -o /dev/null -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"board": {"name": "BOARD_NAME"}}' | grep -i '^location:' | tr -d '\r')
BOARD_ID=$(echo "$LOCATION" | sed 's|.*/boards/||' | sed 's|\.json||')
```
3. Create each column in order (columns are appended after the 3 default columns: Not Now, Maybe?, Done):
```bash
# Run these sequentially — column order = creation order
for COL in \
  '{"column":{"name":"Additional Grooming","color":"var(--color-card-default)"}}' \
  '{"column":{"name":"🟡 Priority","color":"var(--color-card-4)"}}' \
  '{"column":{"name":"🟠 Priority","color":"var(--color-card-3)"}}' \
  '{"column":{"name":"🔴 Priority","color":"var(--color-card-8)"}}' \
  '{"column":{"name":"In Progress","color":"var(--color-card-2)"}}' \
  '{"column":{"name":"PR Open","color":"var(--color-card-6)"}}' \
  '{"column":{"name":"QA Failed","color":"var(--color-card-2)"}}' \
  '{"column":{"name":"QA to be confirmed","color":"var(--color-card-5)"}}' \
  '{"column":{"name":"Merge to Prod","color":"var(--color-card-7)"}}'; do
  curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/${BOARD_ID}/columns.json" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$COL"
done
```
4. Confirm columns were created:
```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/${BOARD_ID}/columns.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json"
```
5. Display the board URL (`https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/${BOARD_ID}`) and column summary to the user.

## Engineering Board Template

The standard column layout used by Vetted and Congrats engineering boards:

| # | Column Name | Color | CSS Variable |
|---|-------------|-------|-------------|
| 1 | Additional Grooming | Blue | `var(--color-card-default)` |
| 2 | 🟡 Priority | Lime | `var(--color-card-4)` |
| 3 | 🟠 Priority | Yellow | `var(--color-card-3)` |
| 4 | 🔴 Priority | Pink | `var(--color-card-8)` |
| 5 | In Progress | Tan | `var(--color-card-2)` |
| 6 | PR Open | Violet | `var(--color-card-6)` |
| 7 | QA Failed | Tan | `var(--color-card-2)` |
| 8 | QA to be confirmed | Aqua | `var(--color-card-5)` |
| 9 | Merge to Prod | Purple | `var(--color-card-7)` |

## Column Colors Reference

| Color Name | CSS Variable |
|------------|-------------|
| Blue (default) | `var(--color-card-default)` |
| Gray | `var(--color-card-1)` |
| Tan | `var(--color-card-2)` |
| Yellow | `var(--color-card-3)` |
| Lime | `var(--color-card-4)` |
| Aqua | `var(--color-card-5)` |
| Violet | `var(--color-card-6)` |
| Purple | `var(--color-card-7)` |
| Pink | `var(--color-card-8)` |

## API Endpoints Reference

### Identity
```bash
curl -s "https://fizzy.do/my/identity" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### List Boards
```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Create Board
Returns `201 Created` with board URL in `Location` header (empty body). Extract board ID from Location.
```bash
curl -s -D - -o /dev/null -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"board": {"name": "My Board"}}'
# Location: /{FIZZY_ACCOUNT_ID}/boards/03f5v9zkft4hj9qq0lsn9ohcm.json
```

### List Columns
```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/{BOARD_ID}/columns.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json"
```

### Create Column
Returns `201 Created` with column URL in `Location` header. Columns are appended in creation order.
```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/{BOARD_ID}/columns.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"column": {"name": "In Progress", "color": "var(--color-card-2)"}}'
```

### Reading a Board (cards + columns) — AUTHORITATIVE

> **This is the single source of truth for reading a board.** `merge-to-prod`, `pr-review`,
> `qa-failed-triage`, `board-cleanup`, and `qa-handoff` all defer here. Four gotchas, every one
> load-bearing — verified against the live API + UI (2026-06).

**1. `board_id` is SILENTLY IGNORED.** `GET /cards.json?board_id={B}` returns cards from *every*
board in the workspace (10 boards, ~440 cards), not the one you asked for. No query param scopes it.
Two correct ways:

- **Per-column (preferred for column-targeted reads — qa-handoff/pr-review/qa-failed-triage/merge-to-prod):**
  properly scoped, and the response carries an exact `X-Total-Count`.
  ```bash
  curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/{BOARD_ID}/columns/{COL_ID}/cards.json" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN" -D /tmp/h.txt -o /tmp/cards.json
  grep -i x-total-count /tmp/h.txt   # exact open-card count for that column (matches the UI badge)
  ```
- **Whole-board (board-cleanup / cross-column sweeps):** walk `/cards.json` and filter client-side
  on `card['board']['name']` (exact names in the Team Boards table above). Match by **exact equality,
  never `startswith`** — sibling boards share a prefix (`Vetted (Recruiter-Facing) | Engineering`,
  `Vetted Onboarding Tool`, `VettedAI GTM` all begin with `Vetted`), so a prefix match silently merges
  multiple boards and inflates every count. Print the distinct matched board names to sanity-check.

**2. Pagination: follow `Link: rel="next"`; page size ESCALATES (15 → 30 → 50 …).** Never hardcode
"15/page" or stop on the first page shorter than 15. Loop until the `Link: rel="next"` header is
absent, then assert fetched count == `X-Total-Count`. A single fetch silently truncates a 44-card
column to its first page.
```bash
url="https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/{BOARD_ID}/columns/{COL_ID}/cards.json"
: > /tmp/col.jsonl
while [ -n "$url" ]; do
  body=$(curl -s "$url" -H "Authorization: Bearer $FIZZY_API_TOKEN" -D /tmp/h.txt)
  echo "$body" | python3 -c "import sys,json;[print(json.dumps(c)) for c in json.load(sys.stdin)]" >> /tmp/col.jsonl
  url=$(grep -i '^link:' /tmp/h.txt | sed -n 's/.*<\([^>]*\)>; *rel="next".*/\1/p')
done
total=$(grep -i x-total-count /tmp/h.txt | tr -d '\r' | awk '{print $2}')
got=$(wc -l < /tmp/col.jsonl)
[ "$got" = "$total" ] || echo "⚠️ TRUNCATED: got $got of $total"
```

**3. The three built-in lifecycle lanes are NOT columns — list them via `indexed_by`, NOT the
per-column endpoint.** `columns.json` returns only the board's *custom* columns, and the
per-column `cards.json` endpoint returns ONLY active cards — it omits Not Now and Done. The
built-in lanes are card flags, and each has its own index lane on the workspace-wide
`/cards.json` endpoint:

| UI lane | Card field | How to list |
|---|---|---|
| **Maybe?** | `column == null` | per-column omits it; appears in whole-board `/cards.json` as a card with `column == null` |
| **Not Now** | `postponed == true` | `GET /cards.json?board_ids[]={B}&indexed_by=not_now` |
| **Done** | `closed == true` | `GET /cards.json?board_ids[]={B}&indexed_by=closed` |

> ⚠️ Corrected 2026-06-29 (was previously documented as "NO list endpoint returns these" —
> that is WRONG). The lane IS listable, but only with the **array** board param `board_ids[]=`
> (the singular `board_id=` from gotcha 1 is still silently ignored) **plus** `indexed_by=<lane>`.
> Verified on the Bugs board: `indexed_by=not_now` → 58 cards (all `postponed:true`),
> `indexed_by=closed` → 135. This is the exact endpoint Basecamp's official
> `fizzy card list --indexed-by` hits.

`indexed_by` lanes: `not_now`, `closed`, `stalled`, `postponing_soon`, `golden`, `all`. **curl
must run with `-g` (globoff)** or it treats `[]` in `board_ids[]` as a glob and sends a broken
URL (silent empty result). Paginate via `Link: rel="next"` exactly as gotcha 2 — these lanes
page too (Not Now was 3 pages). Transition to Done = `POST /cards/{N}/closure.json` (see Close Card).

**Reusable helper:** `scripts/fizzy-lane.sh <board_id> [lane] [format]` wraps this (raw curl,
no CLI dependency — works on CI runners). `lane` defaults to `not_now`; `format` is
`table`|`numbers`|`json`. e.g. `scripts/fizzy-lane.sh 03fl735hqcd0h1pettl8o94oo not_now numbers`.

**4. Auto-postpone makes idle cards VANISH from columns.** Boards carry `auto_postpone_period_in_days`
(`GET /boards/{B}.json` — e.g. 90 on Bugs, 30 on Congrats). A card idle that long auto-moves to
**Not Now**, dropping out of the per-column endpoint (and the active board view). A long-idle card
that "disappeared" from a column was likely auto-postponed, not completed — never infer "shipped"
from its absence. To find it, list the Not Now lane (gotcha 3: `indexed_by=not_now`), don't assume
it's gone.

### List Cards by tag (whole-workspace)
```bash
# board_id is ignored (gotcha 1); the tag filter DOES work. Still filter board.name client-side.
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards.json?tag_ids[]={TAG_ID}" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Get Card by Number

> **`.json` is mandatory on EVERY card/resource endpoint — reads AND writes.** `GET /cards/{N}`, `PUT /cards/{N}`, `POST /cards/{N}/comments`, `/assignments`, `/taggings` etc. all require the `.json` suffix. The bare path is served as a session-authenticated HTML route and rejects the bearer token (GET/PUT → `401 "HTTP Token: Access denied."`; action POSTs → `422`). When any Fizzy call 401/422s for no obvious reason, the first thing to check is a missing `.json`.

```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Create Card

> **Use the helper — it is the only path that VERIFIES the card landed.**
> ```bash
> # Ships with this skill: submodules/skill-master/scripts/fizzy-file-card
> # Put it on PATH once:  ln -sf "$PWD/submodules/skill-master/scripts/fizzy-file-card" ~/.local/bin/
> fizzy-file-card --list-columns --board {BOARD_ID}
> fizzy-file-card --board {BOARD_ID} --column {COLUMN_ID} --title "..." --description-file body.html
> ```
> create → triage → **re-read → assert `column != null`**, exiting non-zero (code 3) if the card
> is floating. The create-then-triage dance below is documented correctly and *still* lost cards
> **#2128 and #2161** (Congrats, 2026-07-17) because nothing verified the result. Documentation
> can't fail; the helper can. Prefer it.

**Important:** Payload must be wrapped in a `card` key (Rails convention). Always include `Accept: application/json`.

Do NOT use `/boards/{BOARD_ID}/columns/{COL_ID}/cards` (that endpoint returns 404 for POST).

**`column_id` in the create payload is SILENTLY IGNORED** — the card lands in the **Maybe?** lane (`column == null`) no matter what you pass. To place it in a column you must **create-then-triage**: POST the card, then `POST /cards/{N}/triage.json` with `{column_id}` (the same endpoint used to move an existing card). Verified 3× 2026-06-22 (#1575/#1576/#1578 all created with `column_id` in the payload, all landed column-less).
```bash
# 1. Create (column_id omitted — it would be ignored anyway); grab N from the Location header
curl -s -D - -o /dev/null -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/{BOARD_ID}/cards.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Card title", "description": "<p>Description here</p>"}}'
# Location: /{FIZZY_ACCOUNT_ID}/cards/{N}.json

# 2. Triage it into the target column
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}/triage.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"column_id": "COL_ID"}'
# 204 No Content

# 3. VERIFY — re-read and assert the card actually landed. DO NOT SKIP.
#    Steps 1-2 were already documented when #2128 and #2161 were lost: a 201 plus a
#    204 still leaves a floating card if the column id was wrong or the triage silently
#    no-op'd. Only this read proves it. (fizzy-file-card does this for you.)
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{N}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0" \
  | python3 -c 'import sys,json; c=json.load(sys.stdin); print("column:", (c.get("column") or {}).get("name") or "❌ FLOATING IN MAYBE PILE")'
```

### Update Card
For title/description/general field updates. **Does NOT accept `column_id`** — use the triage endpoint below to move cards between columns.

**The URL MUST carry the `.json` suffix.** Bare `PUT /cards/{NUMBER}` returns `401 "HTTP Token: Access denied."` — the bearer token is rejected because the bare path is served as a session-authenticated HTML route (same trap as bare-suffix GETs). `PUT /cards/{NUMBER}.json` returns `200`. (Verified 2026-06-18.)

**PUT replaces the ENTIRE card** — any field you omit is wiped to empty. Always GET the card first and resend every field you want to keep (e.g. include the existing `title` when you only mean to change `description`).
```bash
curl -s -X PUT "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Existing title (resend!)", "description": "<p>New HTML body</p>"}}'
```

### Move Card to Column
Use the `triage.json` action endpoint. Returns `204 No Content` on success. `PUT /cards/{N}` with `column_id` returns 400 — don't try it.
```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}/triage.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"column_id": "COL_ID"}'
```

### Close Card (→ Done lane)
"Done" is card closure, not a column move. Returns `204 No Content`. The card leaves its column
and drops out of the per-column endpoint — list it back via `indexed_by=closed` (gotcha 3 above).
```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}/closure.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Add Comment
```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"body": "<p>Comment text (HTML — markdown renders as a blob)</p>"}'
```

### Assign User
Note: POST toggles assignment (assign if unassigned, unassign if assigned). Response is 204 No Content.
```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}/assignments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_id": "USER_ID"}'
```

### Add Tags
```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/{NUMBER}/taggings.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": ["TAG_ID"]}'
```

### List Tags
```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/tags.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### List Users
```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/users.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

## Pagination

List endpoints (cards AND comments) paginate. **Page size escalates (15 → 30 → 50 …), so never
hardcode a per-page size or stop on the first short page.** Follow the `Link` response header until
`rel="next"` is absent, then assert the fetched count == `X-Total-Count`:

```
Link: <https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards?page=2>; rel="next"
```

See **Reading a Board (cards + columns) — AUTHORITATIVE** above for the full paginator and the
`board_id`-ignored / lane-listing-via-`indexed_by` / auto-postpone gotchas.

## Caching

Fizzy supports ETag caching. For repeated queries:
1. Store the `ETag` header from the response
2. On subsequent requests, send `If-None-Match: {etag}`
3. A `304 Not Modified` means data hasn't changed

## Key Notes

- **IDs are strings** (UUIDv7 format, 25-char base36), not integers
- **Card numbers** are sequential integers, unique per account — use these for human references
- **Rich text** fields accept HTML (sanitized server-side). Use `body_html` for cards and comments
- **Errors:** 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 422 (validation error)
- **Array params:** Use bracket notation: `?tag_ids[]=id1&tag_ids[]=id2`
