---
name: ingesting-session-work
description: Use when Tobi says "capture this", "update the wiki", "log what we did", "make sure the wiki knows", "close this out", or is ending a session whose work isn't yet reflected in wiki pages. Reconciles the wiki record with work actually done — updates the pages the session made stale. For parking work so a future session can resume it, use capturing-session-handoffs instead.
version: 1.0.0
license: MIT
---

# Ingesting Session Work

Bring the wiki record up to date with what a session actually did.

This is **not** a pickup note. A pickup note tells a future agent where the work stands; it lives in `NOW.md` and a scratch handoff, and is disposable by design. This skill exists because those artefacts can be perfectly written while the wiki itself still says something false. A session can produce real work and leave the pages describing that work two months behind.

## When To Use

- Tobi says "capture this", "update the wiki", "log what we did", "make sure the wiki knows", "close this out", or similar.
- A session produced deliverables, decisions or status changes that existing wiki pages should reflect.
- **Not** when Tobi wants to park work for later — that's `capturing-session-handoffs`.

### The distinguishing question

> Is this work **parked** (a future session resumes it) or **done** (the record needs updating)?

Parked → `capturing-session-handoffs`. Done → this skill. Both can apply; run this one first, since it's the one whose absence loses history rather than momentum.

## The Failure This Prevents

These are real, from a session that rewrote two CVs and fixed a leak in a document already sent to a partner:

1. **Pages stale behind the work.** `wiki/orgs/shortlist.md` stopped at a July milestone. The entire September arc — associate count agreed, annexure, partner call, JD pack, a document leak — was invisible, even though the session's whole job was downstream of it.
2. **Artefacts stranded in `scratch/`.** A complete, verified deliverable pack sat in a folder that `WIKI.md` calls "disposable — nothing here is canonical". No wiki page pointed at it.
3. **A leak fixed in place, recorded nowhere.** A document already sent to a partner was corrected on disk. Without a wiki entry, no future session knows the copy held by the partner differs from the copy on disk.
4. **A near-miss presented as a decision.** An entity contradiction was spotted during the session and dismissed. Had it gone unrecorded, the next session would have re-derived it from scratch.

The common thread: **the session knew things the wiki didn't.** This skill closes that gap.

## Core Rule

> **Work that isn't in the wiki didn't happen.**

Deliverables in `scratch/` are not a record. A scratch handoff is not a record. The wiki pages are the record. If the wiki read by a fresh agent tomorrow wouldn't know this session occurred, the session isn't captured.

## Workflow

### 1. Orient

From the wiki root:

```bash
ls
sed -n '1,120p' WIKI.md
sed -n '1,80p' NOW.md
```

Read the session's outputs — deliverables, handoff, generator scripts, anything the session produced.

Completion criterion: you can state, in one sentence each, **what changed in the world** and **which wiki pages ought to know about it**.

### 2. Find The Pages That Ought To Know

Do this **before** writing anything. Name the pages by role, not by what the session happened to touch:

| If the session involved… | The page that ought to know |
|---|---|
| A person's work, status, pay or placement | `wiki/people/<person>.md` |
| An external org, partner or funder | `wiki/orgs/<org>.md` |
| A project or workstream | `wiki/projects/<project>.md` |
| A reusable idea, model or decision pattern | `wiki/concepts/<concept>.md` |
| An investigation or open question | `wiki/research/<topic>.md` |

Now read the `updated:` date in each candidate page's frontmatter.

**Any page whose subject matter moved but whose `updated:` date predates the session is a gap.** That is the check that matters. It is what catches the page nobody thought to open.

Completion criterion: a named list of pages to update, each with a reason it's in scope.

### 3. Decide What's Durable vs Disposable

For each artefact the session produced, decide its status — **deliberately, not by default**:

- **Durable** → its substance belongs in a wiki page. Point at the artefact from the page; don't duplicate the whole thing.
- **Disposable** → leave it in `scratch/`. Fine for one-off exports and working files.
- **Durable *and* strategically important** → promote the page per `WIKI.md`, and replace the scratch artefact's role with the page.

A complete deliverable pack that a future session will need is **durable**. It should be reachable from a wiki page, not only from a scratch folder.

Completion criterion: every session artefact is classified, with durable ones linked from a wiki page.

### 4. Snapshot Before Protected Edits

```bash
python3 tools/wiki-safety-snapshot.py
```

Protected files: `NOW.md`, `wiki/log.md`, `wiki/index.md`, `raw/_index.md`, `WIKI.md`.

Completion criterion: the snapshot succeeds and prints its backup directory.

### 5. Update The Record

For each page from step 2:

- Add or extend the section that describes what actually happened. Follow the page format for its type (`WIKI.md` § Page Formats by Type).
- **Record the decision and the reasoning**, not just the outcome. A page that says *what* was done but not *why* forces the next session to re-derive it.
- **Record what was checked and found clean.** "No leaks found across the pack" is worth writing — it stops the next session repeating the scan.
- **Record near-misses and dismissed concerns** with the reason they were dismissed. A dismissed concern recorded is a decision; unrecorded, it's a landmine.
- **Never silently resolve a contradiction** you noticed but didn't act on. Write it down as an open loop.
- Update the `updated:` date in frontmatter.
- Add backlinks, and verify each one resolves.

Then add one `wiki/log.md` entry at the top:

```markdown
[YYYY-MM-DD] [TYPE] Description — what changed, where the artefacts live, what was sent or not sent, live state.
```

Types: `INGEST | QUERY | LINT | UPDATE | TRIAGE | NOTE`.

Completion criterion: every page in scope reflects the session's work, and each has a fresh `updated:` date.

### 6. Flag, Don't Fix, The Sidelines

Do **not** quietly repair unrelated problems found along the way. Surface them:

- **`NOW.md` over threshold** — check line count and session-block count against `WIKI.md` § NOW.md Maintenance. If it's due for a prune, **say so and stop**. Do not append another block to a file already over the limit; do not turn a capture into a pruning session.
- **Unresolved contradictions** between pages.
- **Pages that look stale for reasons unrelated to this session.**
- **Anything you couldn't verify** — a link you couldn't confirm, a fact you inferred.

Completion criterion: sideline issues are reported as a short list, each with a suggested next step, and none were acted on.

### 7. Verify

Re-read every file you edited. Scan for patch debris:

```bash
rg -n "^(<<<<<<<|=======|>>>>>>>|@@|\+)" <touched-files>
```

Confirm frontmatter parses, and that backlinks you added resolve:

```bash
grep -ohE '\[\[[a-z0-9-]+\]\]' <touched-files> | sort -u
```

Any link you cannot confirm exists must be reported, not left as a silent assumption.

Completion criterion: files are readable, no patch markers, and every link is either confirmed or reported.

### 8. Commit

```bash
git add -A <wiki files> <artefacts worth keeping>
git commit -m "<what changed, and the reasoning that isn't obvious from the diff>"
```

This repo is local-only (`WIKI.md` § Local Git Repo) — commits are the cheap safety net, not a publishing event. Commit in a small batch scoped to this session's work. Put the non-obvious reasoning in the commit message; the diff shows what, the message explains why.

Do not commit anything under `raw/` without checking `.gitignore` first.

Completion criterion: one small commit, scoped to this session, with a message a future agent can act on.

## Anti-Patterns

- **Writing a handoff instead of updating pages.** A pickup note beside a stale page is still a stale page.
- **Only updating pages the session touched.** The pages that need updating are often the ones nobody opened — the stale ones.
- **Recording outcomes without reasoning.** Forces the next session to re-derive decisions you already made.
- **Leaving a complete deliverable reachable only from `scratch/`.**
- **Silently fixing a contradiction you weren't asked to fix.**
- **Appending to an over-threshold `NOW.md`.** Flag it instead.
- **Reporting and waiting on the commit.** Report *and* commit, then say what you committed.

## Prompting Note

A capture session's report should be a **map of what the wiki now knows**, not a summary of the conversation. Lead with which pages changed and why they needed to.
