---
name: fizzy
description: Interact with Fizzy (37signals) project management boards via REST API. Use when the user wants to create, read, update, or close Fizzy cards, add comments, check board status, create new boards, or file bugs/features.
---

# Fizzy Project Management Integration

Interact with the team's Fizzy boards directly via the REST API using `curl` or `WebFetch`.

## Authentication

All requests require a Bearer token. Read from the user's environment:

```bash
# Token is in the user's shell environment
echo $FIZZY_API_TOKEN
```

Header: `Authorization: Bearer $FIZZY_API_TOKEN`

> **NEVER hardcode the token.** Always reference `$FIZZY_API_TOKEN`.

## API Base URL

```
https://app.fizzy.do/6102589
```

Account slug: `6102589`

## Team Boards

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
1. Get the Bugs board ID (list boards if needed)
2. Create a card with the description as title + body
3. Add the `bug` tag if available
4. Return the card URL

### `/fizzy feature [description]`
Create a feature card on the Product board.

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
LOCATION=$(curl -s -D - -o /dev/null -X POST "https://app.fizzy.do/6102589/boards" \
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
  curl -s -X POST "https://app.fizzy.do/6102589/boards/${BOARD_ID}/columns" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "$COL"
done
```
4. Confirm columns were created:
```bash
curl -s "https://app.fizzy.do/6102589/boards/${BOARD_ID}/columns" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json"
```
5. Display the board URL (`https://app.fizzy.do/6102589/boards/${BOARD_ID}`) and column summary to the user.

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
curl -s "https://app.fizzy.do/6102589/boards" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Create Board
Returns `201 Created` with board URL in `Location` header (empty body). Extract board ID from Location.
```bash
curl -s -D - -o /dev/null -X POST "https://app.fizzy.do/6102589/boards" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"board": {"name": "My Board"}}'
# Location: /6102589/boards/03f5v9zkft4hj9qq0lsn9ohcm.json
```

### List Columns
```bash
curl -s "https://app.fizzy.do/6102589/boards/{BOARD_ID}/columns" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Accept: application/json"
```

### Create Column
Returns `201 Created` with column URL in `Location` header. Columns are appended in creation order.
```bash
curl -s -X POST "https://app.fizzy.do/6102589/boards/{BOARD_ID}/columns" \
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
  curl -s "https://app.fizzy.do/6102589/boards/{BOARD_ID}/columns/{COL_ID}/cards.json" \
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
url="https://app.fizzy.do/6102589/boards/{BOARD_ID}/columns/{COL_ID}/cards.json"
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

**3. The three built-in lifecycle lanes are NOT columns — and two are invisible to the list API.**
`columns.json` returns only the board's *custom* columns. The built-in lanes are card flags:

| UI lane | Card field | Listable via API? |
|---|---|---|
| **Maybe?** | `column == null` | ✅ yes — returned as open cards with no column |
| **Not Now** | `postponed == true` | ❌ **NO list endpoint returns these** |
| **Done** | `closed == true` | ❌ **NO list endpoint returns these** |

No query param (`closed=true`, `status=closed`, `scope=done`, `filter=not_now`, …) and no
reserved-slug path (`/columns/done/...`, `/closures.json`, …) surfaces Not Now or Done — all
ignored or 404. To read a specific Not Now/Done card you must already know its number:
`GET /cards/{N}.json` (its `postponed`/`closed` flag will be set). The UI is the only place those
two counts are visible. Transition to Done = `POST /cards/{N}/closure.json` (see Close Card).

**4. Auto-postpone makes idle cards VANISH.** Boards carry `auto_postpone_period_in_days`
(`GET /boards/{B}.json` — e.g. 30 on Congrats). A card idle that long auto-moves to **Not Now**,
dropping out of BOTH the per-column endpoint AND the list API. A long-idle card that "disappeared"
from a column was likely auto-postponed, not completed — never infer "shipped" from its absence.

### List Cards by tag (whole-workspace)
```bash
# board_id is ignored (gotcha 1); the tag filter DOES work. Still filter board.name client-side.
curl -s "https://app.fizzy.do/6102589/cards.json?tag_ids[]={TAG_ID}" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Get Card by Number

> **`.json` is mandatory on EVERY card/resource endpoint — reads AND writes.** `GET /cards/{N}`, `PUT /cards/{N}`, `POST /cards/{N}/comments`, `/assignments`, `/taggings` etc. all require the `.json` suffix. The bare path is served as a session-authenticated HTML route and rejects the bearer token (GET/PUT → `401 "HTTP Token: Access denied."`; action POSTs → `422`). When any Fizzy call 401/422s for no obvious reason, the first thing to check is a missing `.json`.

```bash
curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Create Card
**Important:** Payload must be wrapped in a `card` key (Rails convention). Always include `Accept: application/json`.

Do NOT use `/boards/{BOARD_ID}/columns/{COL_ID}/cards` (that endpoint returns 404 for POST).

**`column_id` in the create payload is SILENTLY IGNORED** — the card lands in the **Maybe?** lane (`column == null`) no matter what you pass. To place it in a column you must **create-then-triage**: POST the card, then `POST /cards/{N}/triage.json` with `{column_id}` (the same endpoint used to move an existing card). Verified 3× 2026-06-22 (#1575/#1576/#1578 all created with `column_id` in the payload, all landed column-less).
```bash
# 1. Create (column_id omitted — it would be ignored anyway); grab N from the Location header
curl -s -D - -o /dev/null -X POST "https://app.fizzy.do/6102589/boards/{BOARD_ID}/cards" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Card title", "description": "<p>Description here</p>"}}'
# Location: /6102589/cards/{N}.json

# 2. Triage it into the target column
curl -s -X POST "https://app.fizzy.do/6102589/cards/{N}/triage.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"column_id": "COL_ID"}'
# 204 No Content
```

### Update Card
For title/description/general field updates. **Does NOT accept `column_id`** — use the triage endpoint below to move cards between columns.

**The URL MUST carry the `.json` suffix.** Bare `PUT /cards/{NUMBER}` returns `401 "HTTP Token: Access denied."` — the bearer token is rejected because the bare path is served as a session-authenticated HTML route (same trap as bare-suffix GETs). `PUT /cards/{NUMBER}.json` returns `200`. (Verified 2026-06-18.)

**PUT replaces the ENTIRE card** — any field you omit is wiped to empty. Always GET the card first and resend every field you want to keep (e.g. include the existing `title` when you only mean to change `description`).
```bash
curl -s -X PUT "https://app.fizzy.do/6102589/cards/{NUMBER}.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Existing title (resend!)", "description": "<p>New HTML body</p>"}}'
```

### Move Card to Column
Use the `triage.json` action endpoint. Returns `204 No Content` on success. `PUT /cards/{N}` with `column_id` returns 400 — don't try it.
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/triage.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"column_id": "COL_ID"}'
```

### Close Card (→ Done lane)
"Done" is card closure, not a column move. Returns `204 No Content`. The card leaves its column
and becomes invisible to the list API (gotcha 3 above).
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/closure.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Add Comment
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"body": "<p>Comment text (HTML — markdown renders as a blob)</p>"}'
```

### Assign User
Note: POST toggles assignment (assign if unassigned, unassign if assigned). Response is 204 No Content.
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/assignments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_id": "USER_ID"}'
```

### Add Tags
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/taggings.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag_ids": ["TAG_ID"]}'
```

### List Tags
```bash
curl -s "https://app.fizzy.do/6102589/tags" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### List Users
```bash
curl -s "https://app.fizzy.do/6102589/users" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

## Pagination

List endpoints (cards AND comments) paginate. **Page size escalates (15 → 30 → 50 …), so never
hardcode a per-page size or stop on the first short page.** Follow the `Link` response header until
`rel="next"` is absent, then assert the fetched count == `X-Total-Count`:

```
Link: <https://app.fizzy.do/6102589/cards?page=2>; rel="next"
```

See **Reading a Board (cards + columns) — AUTHORITATIVE** above for the full paginator and the
`board_id`-ignored / Not-Now-&-Done-invisible / auto-postpone gotchas.

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
