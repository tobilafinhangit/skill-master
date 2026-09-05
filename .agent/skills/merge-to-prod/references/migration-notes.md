# Migration assessment notes

## "Additive" is not "safe"

`ADD COLUMN`, `CREATE TABLE`, and `CREATE INDEX` still need the four-part
assessment from Phase 4: compatibility (old code vs new schema, new code vs
unmigrated schema), locking (exclusive locks, table rewrites on hot tables),
prerequisites (extensions, roles, ordering), affected runtime (edge
functions, crons, clients touching the objects). A concurrently-written
default backfill on a large table is the classic "additive but locking"
case. When unsure, assume coupled.

## Postconditions are conjunctive

`verified_applied` needs the key object present on prod AND the registry row
present. Either alone is `partial_or_drifted`: object-without-registry means
hand-applied or out-of-band; registry-without-object means a failed or
rolled-back apply. For `CREATE OR REPLACE` functions, presence means the new
body (match a marker only the new version contains), not the old one.

## Modified or deleted historical migrations

A migration file already on target that changes between base and head is
never routine — it means history was rewritten after apply. Stop and
investigate (which environments applied which version, whether the registry
lies) before anything publishes.

## Coupled checklist shape

Each coupled pair gets ordered steps, one verification query per step, and
one recovery action per step, embedded in the PR body so the person merging
sees it at merge time. Example shape:

1. Apply `<file>` via Dashboard SQL editor → verify with
   `SELECT … FROM information_schema …` → on failure, do NOT merge; the
   schema change alone is inert.
2. Merge PR → verify edge-fn deploy green + smoke query → on failure,
   revert the merge first (code), then assess whether the schema step
   needs a compensating migration (never "roll back" by deleting a
   migration file).
