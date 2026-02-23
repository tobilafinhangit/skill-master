---
name: fizzy
description: Interact with Fizzy (37signals) project management boards via REST API. Use when the user wants to create, read, update, or close Fizzy cards, add comments, check board status, or file bugs/features.
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
```bash
curl -s -X POST "https://app.fizzy.do/6102589/boards/{BOARD_ID}/cards" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Card title", "description": "<p>Description here</p>"}}'
```

### Update Card
```bash
curl -s -X PUT "https://app.fizzy.do/6102589/cards/{NUMBER}" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"card": {"title": "Updated title"}}'
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
```bash
curl -s -X POST "https://app.fizzy.do/6102589/cards/{NUMBER}/assignments" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "USER_ID"}'
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
