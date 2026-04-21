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

### List Cards (with filters)
```bash
# All cards on a board
curl -s "https://app.fizzy.do/6102589/cards?board_id={BOARD_ID}" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"

# Filter by tag
curl -s "https://app.fizzy.do/6102589/cards?board_id={BOARD_ID}&tag_ids[]={TAG_ID}" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Get Card by Number
```bash
curl -s "https://app.fizzy.do/6102589/cards/{NUMBER}" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Create Card
**Important:** Payload must be wrapped in a `card` key (Rails convention). Always include `Accept: application/json`.

Place the card in a specific column by passing `column_id` inside the `card` payload — do NOT use `/boards/{BOARD_ID}/columns/{COL_ID}/cards` (that endpoint returns 404 for POST).
```bash
curl -s -X POST "https://app.fizzy.do/6102589/boards/{BOARD_ID}/cards" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Card title", "description": "<p>Description here</p>", "column_id": "COL_ID"}}'
```

### Update Card
For title/description/general field updates. **Does NOT accept `column_id`** — use the triage endpoint below to move cards between columns.
```bash
curl -s -X PUT "https://app.fizzy.do/6102589/cards/{NUMBER}" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Updated title"}}'
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

### Close Card
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/closure" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
```

### Add Comment
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/comments" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"comment": {"body": "<p>Comment text</p>"}}'
```

### Assign User
Note: POST toggles assignment (assign if unassigned, unassign if assigned). Response is 204 No Content.
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/assignments" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"assignee_id": "USER_ID"}'
```

### Add Tags
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/taggings" \
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

List endpoints return paginated results. Check the `Link` response header for the next page:

```
Link: <https://app.fizzy.do/6102589/cards?page=2>; rel="next"
```

Follow `rel="next"` links to get all results.

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
