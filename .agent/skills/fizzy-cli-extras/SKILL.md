---
name: fizzy-cli-extras
description: |
  Thin wrapper around Basecamp's `fizzy` CLI (https://github.com/basecamp/fizzy-cli) for
  surface area the existing `/fizzy` skill does NOT cover: cross-board search, file uploads,
  and multi-account auth juggling (Vetted ↔ Congrats Fizzy contexts). For ALL other Fizzy
  actions (cards, comments, columns, board/column IDs, user IDs, engineering board template,
  column-move via POST /triage.json, comment HTML formatting, etc.) defer to `/fizzy`.
triggers:
  - fizzy search
  - fizzy upload
  - fizzy auth
  - fizzy identity
  - search fizzy cards
  - find fizzy card
  - upload to fizzy
invocable: true
---
> **Note:** This skill references `.claude/rules/*.md` files from the original author's private repos — optional deep-dive context, not required. If those files aren't present in your repo, follow the inline instructions in this skill directly.


# fizzy-cli-extras

Adjunct to `/fizzy`. Covers ONLY: search, upload, auth/identity.

For cards/comments/columns/boards/assignments → use **`/fizzy`** (still the authority).
For edge-function Fizzy calls → use `supabase/functions/_shared/fizzyClient.ts` (CLI can't run in Deno).

## Hard rules

1. **Never run `fizzy auth login`.** Token resolves via the `fizzy()` shell function in `~/.zshrc` which reads `FIZZY_API_TOKEN` from the current repo's `.env.local`. Two token stores = drift.
2. **Always guard CLI invocations** with availability check — CI runners and teammates without the local install must still work:
   ```bash
   if ! command -v fizzy >/dev/null 2>&1; then
     echo "fizzy CLI not installed — use /fizzy raw-curl patterns instead"
     exit 1
   fi
   ```
3. **Never edit submodule `/fizzy` skill** to call this CLI. This skill is project-local on purpose. Cross-repo coupling stays via the existing submodule.
4. **Don't upgrade fizzy without re-running impact analysis** — JSON shape changes can break dependent skills silently. v3.0.3 is the validated version as of this skill's authoring.
5. **Defer to `/fizzy`** for any action this skill's triggers don't explicitly cover. Do not re-implement card/comment/column commands here.

## Token + account setup (one-time, outside the agent)

Install:
```bash
curl -fsSL https://raw.githubusercontent.com/basecamp/fizzy-cli/master/scripts/install.sh | bash
# Binary lands at ~/.local/bin/fizzy
```

Add to `~/.zshrc` (PATH first, function second):
```bash
export PATH="$HOME/.local/bin:$PATH"

fizzy() {
  local dir="$PWD"
  local token=""
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/.env.local" ]; then
      token=$(grep ^FIZZY_API_TOKEN "$dir/.env.local" 2>/dev/null | cut -d= -f2- | tr -d '"')
      break
    fi
    dir=$(dirname "$dir")
  done
  if [ -n "$token" ]; then
    FIZZY_TOKEN="$token" FIZZY_ACCOUNT={FIZZY_ACCOUNT_ID} command fizzy "$@"
  else
    command fizzy "$@"
  fi
}
```

Reload + verify:
```bash
source ~/.zshrc
cd ~/code/repos/vettedai-audition-supabase-version
fizzy board list   # should return 9 boards
```

The function walks up from `$PWD` to find `.env.local`, so it works from any of the three Fizzy-enabled repos (vettedai-audition, congrats, backend-restructing). Account `{FIZZY_ACCOUNT_ID}` is a placeholder — swap in your own Fizzy account slug and keep it consistent across your Fizzy-enabled repos.

## What this skill does NOT do

| Action | Use instead |
|--------|-------------|
| Create/move/comment on cards | `/fizzy` |
| Assign Elvis (QA) or Oussama (backend) | `/fizzy` (user IDs live there) |
| Look up board/column IDs (Bugs, Vetted, Congrats, Product) | `/fizzy` |
| Engineering board column template | `/fizzy` |
| Edge-function Fizzy calls | `supabase/functions/_shared/fizzyClient.ts` |
| CI/GitHub Actions Fizzy calls | Raw curl (CLI not installed on runners) |
| Webhooks | Not in v3.0.3; use raw API or wait for upstream |
| Tags / notifications / pins / reactions | CLI supports these but we don't automate them — use `/fizzy` curl if needed |

## Commands this skill covers

### Search (the flagship — no equivalent in `/fizzy`)

```bash
fizzy search "<query>"                  # cross-board search
fizzy search "<query>" --board <id>     # scoped to a board
```

Use when: finding cards by content across boards without knowing the card number. Faster than scrolling Fizzy UI. Output is JSON; pipe to `jq`:

```bash
fizzy search "P0" | jq '.data[] | {number, title, board: .board.name}'
```

### Upload (file attachments)

```bash
fizzy upload <file>                    # uploads a file to Fizzy storage, returns a reference
fizzy card update <card> --attach ...  # attach an uploaded file to a card
```

Use when: posting screenshots, logs, or other binary artifacts to a card. The pure-REST flow for this was undocumented in `/fizzy` and would have required multipart upload handling.

### Auth / identity (multi-account juggling)

```bash
fizzy auth status         # current auth state
fizzy identity            # show current user + account info
```

Use when: confirming which Fizzy account the CLI is hitting. Note: the `fizzy()` function in `~/.zshrc` hardcodes `FIZZY_ACCOUNT={FIZZY_ACCOUNT_ID}` — replace with your own account slug. If you ever need a different account, edit the function — don't run `fizzy auth login`.

## Output format

CLI emits JSON by default. Every response wraps in `{success, data}`. Pipe to `jq` for parsing:

```bash
fizzy board list | jq '.data[] | {name, id}'
fizzy search "auth" | jq '.data | length'
```

## Failure modes + fallbacks

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `command not found: fizzy` | CLI not installed on this machine | Fall back to `/fizzy` raw-curl patterns; do not block on install |
| `Not authenticated` from `fizzy auth status` | `.env.local` missing in this dir tree, or `FIZZY_API_TOKEN` blank | `cd` to a repo that has `.env.local`; verify `grep ^FIZZY_API_TOKEN .env.local` returns a value |
| `No account configured` | Function didn't set `FIZZY_ACCOUNT` | Check `~/.zshrc` function still hardcodes your `FIZZY_ACCOUNT` |
| CLI hangs on network | Flaky connection | `Ctrl+C` and retry; wrap unattended calls with `timeout 30s fizzy ...` |
| Output JSON shape changed unexpectedly | Newer CLI version installed | Check `fizzy version`; this skill validated against v3.0.3 |

## When to expand this skill's scope

Phase 3 of the rollout plan may migrate ONE call site in `/qa-handoff` (the comment-post step) to `fizzy comment create` — gated behind the `command -v fizzy` guard above. That migration lives in the submodule `/qa-handoff` skill, NOT here. This skill's surface stays narrow until a Phase 4 decision gate re-runs impact analysis.

## References

- CLI repo: https://github.com/basecamp/fizzy-cli
- Validated CLI version: **v3.0.3**
- Existing `/fizzy` skill (authoritative for cards/comments/columns): `submodules/skill-master/.agent/skills/fizzy/SKILL.md`
- Raw API gotchas: `.claude/rules/fizzy-api-patterns.md` (still authoritative for `/fizzy` and `fizzyClient.ts`)
- Edge fn client: `supabase/functions/_shared/fizzyClient.ts`
