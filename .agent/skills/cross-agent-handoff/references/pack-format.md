# Handover archive format

Use a tracked archive with this shape:

```text
README.md
config/handoff-scope.yml
handoffs/YYYY/YYYY-Www/
  00-index.md
  source-inventory.md
  release-reconciliation.md       # only when release/live claims exist
  01-<workstream>.md
  02-<workstream>.md
```

For a custom period, replace `YYYY-Www` with `YYYY-MM-DD_to_YYYY-MM-DD`. Keep all dates in the archive timezone.

## `00-index.md`

```markdown
# Coding-work handover — <period>

## Start here

1. Read the target repository instructions and the named read-first files.
2. Treat evidence labels literally; re-check all unknown or transcript-reported live claims.
3. Begin with the top active priority below.

## Active pickup queue

| Priority | Workstream | Current state | Read |
|---|---|---|---|
| P0 | <name> | <one-line truth> | [brief](01-example.md) |

## Scope and exclusions

- In scope: <repositories/sources>
- Excluded: <repositories/locations>
- Sources inspected: <count and identifiers>
```

## `source-inventory.md`

Record every inspected source, even when it was excluded or folded into another brief:

```markdown
| Date/time | Agent | Session/source ID | Repository | Classification | Destination |
|---|---|---|---|---|---|
| <time> | Codex | `<id>` | <repo> | Folded into <workstream> | [brief](01-example.md) |
```

## Workstream brief

```markdown
# Pickup brief — <workstream>

## Current state

<Evidence-backed summary. Include the evidence label.>

## Completed / evidence

- **Repository-verified:** <fact and reference>
- **Transcript-reported:** <fact and source>
- **Unknown:** <what must be checked>

## Open loops and exact next action

1. <Smallest safe first action.>

## Do not do

- <Unsafe inference or mutation to avoid.>

## Read first

- `<absolute or repository-relative path>`
- PR/card/branch/deployment references

## Sources

- `<agent/session ID>` — <what it contributed>
```

## `release-reconciliation.md`

Use this page only if a workstream contains a merge, deployment, migration, CI, QA, or production claim. Keep merge ancestry, live deployment state, and QA evidence in separate columns. A merge is not evidence of a deployment or release.
