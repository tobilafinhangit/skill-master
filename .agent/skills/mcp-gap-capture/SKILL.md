---
name: mcp-gap-capture
description: Capture capability gaps in the Vetted MCP — when you (the agent) wanted to use a Vetted MCP tool but it didn't exist or wasn't sufficient and you fell back to raw Supabase MCP, direct SQL, or manual work. Logs a redacted, de-duplicated gap record to a shared JSONL sink so we can see "most-requested missing Vetted MCP capabilities" across all sessions/repos. Use when bypassing the Vetted MCP, as a live self-review (scans the current session's own tool calls — no user description needed), or at session end as a backstop sweep.
version: 1.1.0
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
- **Live self-review (invoke `/mcp-gap-capture`):** scan the *current* session's own
  conversation + tool calls (already in your context) for Vetted-MCP bypasses and log them.
  No user description needed — see Session Self-Review.
- Explicitly via `/mcp-gap-capture`.

## Session Self-Review (no user description needed)

When invoked in a live session, you already have the conversation and tool calls in context.
Use them — do NOT ask the user to describe gaps.

1. Scan the session for every place you used **Supabase MCP**, **raw SQL**, or **manual
   work** (DB queries, schema poking, candidate/project lookups done outside the Vetted
   `vetted_*` tools).
2. For each, ask: *should a Vetted MCP tool (`vetted_*`) have covered this?* If you clearly
   expected (or wished for) a specific Vetted tool, that's the gap.
3. Classify per Two-Tier Detection below:
   - **Tier 1 (high):** you know the intent + the missing/existing tool — log directly.
   - **Tier 2 (low):** unsure it "should have been" Vetted — run `log_gap.mjs --dry`, show
     the user, log only after confirm.
4. Call `log_gap.mjs` per gap (see How to Log). Pass `--agent` for the current agent; `repo`
   comes from the repo's `.mcp-gap-capture.json`.

This is the most reliable mode — the agent knows its own intent, so no transcript file is
needed. It still can't see "intended but never attempted" work that left no trace in the
conversation, and it's still self-reported (not a measured call-stream diff).

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

## Triage context (for the reviewing engineer)

A gap line without repro steps is a riddle for whoever picks it up. Assume a different
engineer will triage it with no access to your session. Always add these on Tier 1
(high-confidence) gaps; add them on Tier 2 whenever you have them:

- `--repro`: minimal steps to hit the gap (tool called, arguments that matter, the exact
  error or response). IDs (project/candidate/run UUIDs) are welcome — they are not PII.
  Never paste emails, phones, tokens, or raw SQL — the logger redacts them anyway.
- `--expected`: what the tool should have done instead.
- `--impact`: who is blocked and what it costs (burned unlocks, unsent outreach, manual
  UI workarounds, misattributed funnel data).
- `--session <id>`: pin a stable session label when logging several related gaps so they
  read as one story instead of scattered lines (the default is a random id per call).

```bash
node .claude/skills/mcp-gap-capture/log_gap.mjs \
  --intent "invite applied-never-invited row via bulk path; no-match" \
  --attempted-tool "vetted_candidates_bulkInvite" \
  --fallback-path "manual" \
  --confidence high \
  --repro "candidates_find + candidates_details resolve the row; bulkInvite with its projectCandidateId returns 'No matching candidates found'; nudge on the same id fails identically" \
  --expected "bulkInvite matches any row in the project, or returns a reason (e.g. ineligible-status) instead of a bare no-match" \
  --impact "recruiter falls back to UI invite; funnel misattributes the candidate as organic" \
  --session "paystack-dba-20260909"
```

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
  "confidence": "high", "ticket": "optional",
  "repro": "<optional, redacted, ≤1000c>", "expected": "<optional, redacted, ≤1000c>",
  "impact": "<optional, redacted, ≤1000c>" }
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
