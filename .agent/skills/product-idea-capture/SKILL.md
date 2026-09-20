---
name: product-idea-capture
description: Capture general Vetted product ideas and gaps — a product behaviour that should change (not a missing MCP tool). Logs a redacted, de-duplicated record to a shared JSONL sink. Use when a product observation, idea, or UX gap surfaces while using Vetted and it isn't a Vetted-MCP tooling gap (that's /mcp-gap-capture).
---

# Product Idea Capture

Sibling of `mcp-gap-capture`. That skill captures **MCP tooling** gaps (a tool the agent wanted and didn't have). This one captures **product** observations — UX and behaviour on the Vetted app itself that a human or agent noticed and thinks should change: a confusing flow, a missing auto-refresh, a merge that loses data, a report that won't render.

Both write redacted JSONL to shared sinks in the wiki. Keep them separate: a product gap can be real even when every MCP tool worked perfectly.

## When to Use

- **Just-in-time (primary):** the moment you (agent) or the user notices something about Vetted's behaviour that should change — log it then, while the detail is fresh.
- **Session-end sweep (backstop):** near the end of a session, review product observations raised in the conversation and log any that aren't yet recorded.
- **Live self-review (invoke `/product-idea-capture`):** scan the current session's own conversation for Vetted product observations and log them. No user description needed.
- Explicitly via `/product-idea-capture`.

Do **not** use this for MCP tooling gaps — that's `/mcp-gap-capture`.

## Two-Tier Detection (false-positive gate)

- **Tier 1 — high confidence (auto-log):** you observed a concrete product behaviour and can state what it does today and what it should do. Log directly.
- **Tier 2 — low confidence (confirm first):** a vague unease ("this felt clunky") with no crisp expected behaviour. Run in `--dry` mode, show the user, log only after they confirm.

## How to Log

Use the bundled `log_idea.mjs` (no DB, no credentials — appends to a JSONL file):

```bash
# High confidence — log directly
node .claude/skills/product-idea-capture/log_idea.mjs \
  --type gap \
  --area "candidate read / AI synthesis" \
  --title "Candidate read should auto-regenerate when new evidence lands" \
  --observation "Uploading a transcript did not refresh the read; needed a manual Regenerate read click." \
  --expected "Any newly ingested evidence (transcript, resume, audition) should auto-regenerate the read, forward and backward in time." \
  --impact "Reviewers see a stale or empty read unless the recruiter remembers to regenerate." \
  --product vetted \
  --session "farmslate-transcript-upload-20260920"

# Low confidence — dry run first, confirm with user
node .claude/skills/product-idea-capture/log_idea.mjs --dry \
  --type observation --area "..." --title "..." --observation "..."
```

- `type`: `gap` | `idea` | `observation`
- `area`: the feature area (e.g. `candidate read / AI synthesis`, `candidate merge / dedupe`, `sourcing`, `outreach`). Used for the rollup — reuse existing areas where they fit.
- `product`: defaults to `vetted` (set it if the observation is about another product).
- `status`: defaults to `open` (use `closed` when a logged item ships or is rejected).

## Triage context (for whoever picks it up)

Assume a different person triages this with no access to your session. Always add:

- `--observation`: what happens today, concretely (the trigger + the symptom).
- `--expected`: what it should do instead.
- `--impact`: who is affected and what it costs (manual workarounds, stale views, lost data).

```bash
node .claude/skills/product-idea-capture/log_idea.mjs \
  --type gap --area "candidate merge / dedupe" \
  --title "Profile merge should carry all candidate data" \
  --observation "Merge appears to keep only sourcing info; other fields on the losing record can be dropped." \
  --expected "Merge all candidate data (details, notes, transcripts, attachments); on conflict, show a UI to pick which version wins." \
  --impact "Merged profiles lose context; transcripts/notes can be silently lost." \
  --session "farmslate-transcript-upload-20260920"
```

The sink path is resolved (in order): `--sink` → `.product-idea-capture.json` in cwd →
`$PRODUCT_IDEA_SINK` → default `_tobi_wiki/wiki/product-ideas.jsonl`. Per-repo config lives in
`.product-idea-capture.json` (`{ "sink": "...", "repo": "..." }`).

## Privacy (mandatory)

`log_idea.mjs` redacts before writing — never bypass it by writing the file directly:
- Emails, phones, JWTs, long secrets → `[redacted-*]`.
- Any string containing raw SQL → `[sql-omitted]`.
- `title` truncated to 300 chars; `observation`/`expected`/`impact` to 1000.

## Schema (one JSONL line)

```json
{ "ts": "ISO", "repo": "tobi_wiki", "agent": "opencode", "session_id": "sess-ab12cd",
  "type": "gap", "area": "candidate merge / dedupe", "status": "open",
  "title": "…", "observation": "…", "expected": "…", "impact": "…",
  "product": "vetted", "ticket": "optional" }
```

## Rollup

Rank open items by area to see where product pain clusters:

```bash
node .claude/skills/product-idea-capture/rollup.mjs
node .claude/skills/product-idea-capture/rollup.mjs /path/to/product-ideas.jsonl
```

## Propagation

This skill lives in `skill-master` and is distributed to all repos via `distribute-skill`. The sink is the wiki JSONL — a single shared location with no RLS, no service-role key, no migration. Fizzy tickets are NOT auto-created; promote an item to a card manually if it warrants build work.
