---
name: mcp-gap-capture
description: Capture capability gaps in the Vetted MCP — when you (the agent) wanted to use a Vetted MCP tool but it didn't exist or wasn't sufficient and you fell back to raw Supabase MCP, direct SQL, or manual work. Logs a redacted, de-duplicated gap record to a shared JSONL sink so we can see "most-requested missing Vetted MCP capabilities" across all sessions/repos. Use when bypassing the Vetted MCP, or at session end as a backstop sweep.
version: 1.0.0
---

# MCP Gap Capture

The Vetted MCP server telemetry (#3232) logs only calls that *reach* the server. It is
blind to the moment an agent gives up on the Vetted MCP and drops to Supabase MCP / raw SQL /
manual work. This skill captures that blind spot: the agent's *intent* when it couldn't use
Vetted MCP. It is self-reported (not server-measured) — treat it as signal about intent, not
an audit trail.

## When to Use

- **Just-in-time (primary):** the moment you decide to use Supabase MCP / raw SQL / manual
  work for something you'd expect a Vetted MCP tool to cover. Capture it *then* — context is
  freshest.
- **Session-end sweep (backstop):** near the end of a session, review what you did via
  Supabase MCP / SQL and log any that "should have been" a Vetted MCP tool.
- Explicitly via `/mcp-gap-capture`.

## Two-Tier Detection (false-positive gate)

- **Tier 1 — high confidence (auto-log):** a Vetted MCP `tools/call` returned
  `unknown_tool` / `tool_error` / `exception`, OR you clearly expected a specific Vetted tool
  to exist. Log directly.
- **Tier 2 — low confidence (confirm first):** you used Supabase MCP / SQL for something a
  Vetted tool *might* cover, but you're not sure it "should have been" Vetted. Run in
  `--dry` mode and show the user what you'd log; only write after they confirm. This mirrors
  the `confirmed:false` dry-run pattern in `fn_mcp_server`.

Do NOT log legitimate non-Vetted work (e.g. poking schema with `describeSchema` when you
never expected a Vetted tool). When in doubt, use Tier 2.

## How to Log

Use the bundled `log_gap.mjs` (no DB, no credentials — appends to a JSONL file):

```bash
# High confidence — log directly
node .claude/skills/mcp-gap-capture/log_gap.mjs \
  --intent "wanted to bulk-export shortlist with contact info for a project" \
  --attempted-tool "vetted_candidates_getShareLink" \
  --fallback-path "supabase_mcp" \
  --confidence high \
  --repo "vettedai-audition"

# Low confidence — dry run first, confirm with user
node .claude/skills/mcp-gap-capture/log_gap.mjs --dry \
  --intent "..." --attempted-tool "unknown" --fallback-path "raw_sql" --confidence low
```

`fallback_path` is one of: `supabase_mcp` | `raw_sql` | `manual` | `other`.
`attempted_tool`: the Vetted MCP tool name you expected (or `unknown`).
Optional `--ticket <fizzy-id>` if you also filed a card manually.

The sink path is resolved (in order): `--sink` → `.mcp-gap-capture.json` in cwd →
`$MCP_GAP_SINK` → default `_tobi_wiki/wiki/mcp-gaps.jsonl`. Per-repo config lives in
`.mcp-gap-capture.json`.

## Privacy (mandatory)

`log_gap.mjs` redacts before writing — never bypass it by writing the file directly:
- Emails, phones, JWTs, and long secrets → replaced with `[redacted-*]`.
- Any string containing raw SQL → replaced with `[sql-omitted]`.
- `intent` is truncated to 200 chars.

## Schema (one JSONL line)

```json
{ "ts": "ISO", "repo": "vettedai-audition", "agent": "opencode",
  "session_id": "sess-ab12cd", "intent": "<redacted, ≤200c>",
  "attempted_tool": "vetted_candidates_top", "fallback_path": "supabase_mcp",
  "confidence": "high", "ticket": "optional" }
```

## Rollup

Rank gaps by requested tool to find what to build next:

```bash
node .claude/skills/mcp-gap-capture/rollup.mjs
# or point at a specific sink:
node .claude/skills/mcp-gap-capture/rollup.mjs /path/to/mcp-gaps.jsonl
```

## Propagation

This skill lives in `skill-master` and is distributed to all repos (this one, Congrats,
`_tobi_wiki`) via `distribute-skill`. The sink is the wiki JSONL — a single shared location
with no RLS, no service-role key, no migration. Fizzy tickets are NOT auto-created (deliberate
#3232 cut); promote a gap to a card manually if it warrants build work.
