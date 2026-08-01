---
name: cross-agent-handoff
description: Reconcile coding work across Codex, Claude, DeepSeek, and other agent sessions into a git-tracked, agent-neutral handover pack. Use when the user asks to hand off one session, a date range, recent activity, pasted transcripts, or an existing handover to another coding agent; group work by workstream, verify repository evidence, and preserve clear pickup actions.
---

# Cross-Agent Handoff

Create an evidence-backed coding-work handover that another agent can use without reading old chats. This skill is independent of personal wiki/session logging workflows.

## Operating modes

Choose the smallest mode that matches the request:

| Mode | Use when | Result |
|---|---|---|
| **Single session** | The user provides one session/transcript. | Add or update the relevant workstream brief. |
| **Period** | The user specifies dates, “recent activity,” or a weekly window. | Inventory all in-scope sessions, then create/update a period pack. |
| **Update** | The user provides new sources for an existing pack. | Reconcile the affected workstreams in place and preserve prior evidence. |
| **Live reconciliation** | The user wants a previous pack checked against current state. | Refresh PR/Git/issue/deploy/QA claims without re-ingesting every source. |

Use the user’s exact time window when supplied. Otherwise ask whether to use an ISO week in the configured timezone; do not silently choose a broad historical period. A period pack can combine any number of repositories, but exclude locations the user explicitly names as out of scope.

## Read configuration and establish scope

1. Locate the configured handover archive and read its `README.md` and `config/handoff-scope.yml` before writing.
2. Confirm the requested source set: supplied attachments/transcripts, provided session IDs, recent activity, and/or a date range.
3. List in-scope repositories and explicit exclusions. Respect repository-local instructions before inspecting code or Git state.
4. Name the period consistently:
   - ISO week: `YYYY-Www`.
   - Custom period: `YYYY-MM-DD_to_YYYY-MM-DD`.
   - Single session/update: update the named existing period; otherwise use the date of the session in the configured timezone.

Do not put raw credentials, secrets, customer data, or full unneeded transcripts in the archive. Store source identifiers/attachment paths and a concise evidence summary instead.

## Gather evidence

For each source, capture its title/identifier, time, repository/worktree, stated outcome, and references to branches, commits, PRs, cards, tests, migrations, deployments, or incidents.

When available, use the native source rather than a pasted summary:

- Codex: read supplied task IDs; for a period, query recent activity and filter by configured repositories/exclusions.
- Other agents: use supplied exports/transcripts and identify their session IDs if present.
- Repositories: inspect the current branch, working-tree state, local refs/ancestry, relevant files, and existing planning artifacts.
- Live systems: query only the exact PR/issue/CI/deployment state required to resolve a material claim and only through the repository’s approved workflow.

Never infer that a merged branch is deployed, a passed test is released, or a transcript claim is current. Do not perform deployments, database writes, ticket changes, pushes, or broad external mutation while gathering evidence unless the user separately asks.

## Reconcile and group

Group sources by **workstream**, not by agent or chat. A workstream may have multiple source sessions and repositories.

For every material claim, label it exactly one of:

- **Repository-verified** — local repository/ref/artifact evidence was checked in this run.
- **Live-verified** — current external state was re-queried in this run.
- **Transcript-reported** — an agent said it happened, but it was not independently rechecked.
- **Unknown** — no adequate evidence exists.

Preserve disagreements. When sources conflict, state the conflict and make the next action a targeted verification, not a guess. Treat an unmerged branch plus a claimed production action as a reconciliation problem.

## Write or update the pack

Use the archive layout and templates in [references/pack-format.md](references/pack-format.md). A period pack must contain an index, a source inventory, a release/deployment reconciliation page when relevant, and one brief for each actual workstream.

Each workstream brief must state:

- current state and evidence label;
- completed work versus transcript claims;
- open loops and the exact first pickup action;
- safety constraints / “do not do”; and
- read-first paths, branch/PR/card/deployment references, and source session IDs.

For an **update**, read the existing index and affected briefs first. Amend the current state and add a dated `## Update — YYYY-MM-DD` section when the history matters. Do not overwrite earlier evidence, duplicate a workstream because another agent used a different title, or downgrade a verified fact without explaining why.

Keep the index short and priority-ordered. Completed one-off fixes belong in reconciliation/history, not the active pickup queue.

## Verify and hand off

1. Re-read every changed Markdown file.
2. Scan for patch markers and run `git diff --check` in the archive.
3. Confirm the archive files are not ignored and report `git status --short`.
4. Report: the archive path, period covered, sources inspected, evidence limitations, active priority order, and any credentials/access needed for remote publication.

Do not automatically commit, push, create a remote repository, deploy, or mutate a live system. If the user asks for a remotely accessible handover, prepare the archive as a clean commit-ready change and request/perform the explicit commit-and-publish step separately.

## Related workflows

- Use repository-specific handoff or ticket skills only after this skill has established the correct workstream and current state.
- Use `capturing-session-handoffs` only for its own Wiki-oriented destination; do not route cross-agent coding handovers there by default.
