---
name: migration-verify
description: Use when a pull request contains database migrations, after a migration merge, or when confirming staging and production schema registry state. Verifies application without applying migrations.
version: 1.0.0
license: MIT
---

# Migration Verify

Treat “merged” and “applied” as separate facts. This skill is read-only: it must never run a migration, `db push`, `db reset`, or make a production schema change.

## Verify

1. Read the repository’s migration, credentials, deployment, and environment rules. Confirm the staging and production project identities before querying either.
2. Identify the migration versions in scope from the PR diff or repository migration directory. Include every timestamped migration file, not just the first one changed.
3. Query `supabase_migrations.schema_migrations` in staging and production with a read-only credential or the repository’s approved management connector. Bound the result to the versions in scope when possible.
4. If the repository provides `npm run verify:migration-application`, run it with a fresh `SUPABASE_ACCESS_TOKEN`; it compares all tracked migration versions with both configured projects. Never echo tokens.
5. Report each environment separately: applied versions, missing versions, and any uncertainty about project identity or credential scope.

## Decision

- Both environments contain every in-scope version: verification passes.
- Either environment is missing a version: verification fails. State the exact gap and stop; request explicit authorization before any Dashboard SQL action.
- Registry data conflicts with observed live schema: report registry drift. Do not infer that a migration is safe to re-run; follow the repository’s migration-registry and deployment rules.

For a migration coupled to an edge-function writer, also follow the repository’s atomic migration-and-writer deployment rule. Registry presence alone is not deployment proof.
