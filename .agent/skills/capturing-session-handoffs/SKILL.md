---
name: capturing-session-handoffs
description: Use when Tobi asks to log where a session is, create a pickup note, park a workstream, preserve context for a new session, or avoid losing work across Codex/Claude sessions.
version: 1.0.0
license: MIT
---

# Capturing Session Handoffs

Create a durable pickup trail so Tobi or another agent can resume work without hunting through old sessions.

## When To Use

- Tobi says "log where we are", "make a pickup note", "park this", "save the context", "so I can pick this up in a new session", or similar.
- A session produced decisions, Fizzy cards, repo findings, PR state, or open loops that should not disappear.
- Before ending a substantial workstream where the next action depends on state discovered in this session.

## Core Rule

`NOW.md` is the canonical pickup index. A scratch handoff file is optional detail. Durable knowledge belongs in `wiki/`, not only in `scratch/`.

## Workflow

### 1. Orient

From the wiki root:

```bash
ls
sed -n '1,220p' WIKI.md
sed -n '1,80p' NOW.md
```

Read any session artifacts, Fizzy cards, PRs, or repo files needed to state the current truth. Do not rely only on conversation memory when local artifacts exist.

Completion criterion: you can name the current state, live external state, open loops, and exact next action.

### 2. Choose Capture Depth

- **Tiny session:** update `NOW.md` only. Add `wiki/log.md` only if the note is reusable or operationally important.
- **Substantive workstream:** create `scratch/<topic-slug>-session-handoff-YYYY-MM-DD.md`, update `NOW.md`, and add one concise `wiki/log.md` line.
- **Durable strategic knowledge:** promote the substance into `wiki/research/`, `wiki/projects/`, or `wiki/concepts/`, then point to that page from `NOW.md`.

Use topic-first filenames:

```text
scratch/<topic-slug>-session-handoff-YYYY-MM-DD.md
```

Example:

```text
scratch/vettedai-ai-routing-session-handoff-2026-07-21.md
```

Completion criterion: the chosen capture depth matches the session's reuse value and does not create scratch clutter for tiny sessions.

### 3. Snapshot Before Protected Edits

Before editing any protected wiki file, run:

```bash
python3 tools/wiki-safety-snapshot.py
```

Protected files include:

- `NOW.md`
- `wiki/log.md`
- `wiki/index.md`
- `raw/_index.md`
- `WIKI.md`

Completion criterion: the snapshot command succeeds and prints a backup directory.

### 4. Write The Handoff

Every substantive handoff must answer:

- **Current state:** where the work stands now.
- **Done:** what was actually completed.
- **Parked:** what is intentionally paused.
- **Open loops:** what still needs a human/agent decision.
- **Next action:** the exact first thing a new session should do.
- **Do not do:** premature or unsafe next steps to avoid.
- **Live state:** Fizzy card numbers, PRs, branches, deploy state, repo paths, blockers, owners.
- **Read first:** the files/cards/pages a new session should open before acting.

For `NOW.md`, add a compact top block:

```markdown
---
[YYYY-MM-DD] [Agent - topic]
**Focus:** ...
**Done:** ...
**Open loops:** ...
**For next agent:** ...
---
```

For `wiki/log.md`, add one concise line at the top when the session created reusable operational knowledge:

```markdown
[YYYY-MM-DD] [HANDOFF] Topic - summary, artifact path, live cards/PRs, and next action.
```

Do not auto-commit. Report that the handoff is written and uncommitted. If the handoff promoted durable `wiki/` pages or changed important project state, recommend a commit and wait for Tobi to ask.

Completion criterion: a new agent can resume from `NOW.md` without reading the old chat.

### 5. Verify

Re-read every protected file you edited:

```bash
sed -n '1,80p' NOW.md
sed -n '1,40p' wiki/log.md
```

Scan touched Markdown files for patch markers or accidental diff debris:

```bash
rg -n "^(<<<<<<<|=======|>>>>>>>|@@|\\+)" <touched-files>
```

If `NOW.md` is over the maintenance threshold from `WIKI.md`, mention it, but do not turn a handoff into a pruning session unless Tobi asked for maintenance.

Completion criterion: edited files are readable, no patch markers are found, and any maintenance warning is reported.

## Resume From A Handoff

When Tobi asks to resume/pick up a prior handoff:

1. Read `WIKI.md`.
2. Read the top block of `NOW.md`.
3. Open the referenced handoff file or durable wiki page.
4. Verify live external state before acting, especially Fizzy cards, PRs, branches, and deployments.
5. Continue from the recorded next action. Do not re-groom or restart unless the handoff says the plan was uncertain.

Completion criterion: the first action matches the handoff's stated next step and current live state.
