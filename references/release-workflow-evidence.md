# Release workflow evidence

The shared checkpoint is versioned JSON. It contains `schema_version`, `repository`, PR/direct revision identity, `card_ids`, `revisions`, `requirements`, `findings`, `coverage`, `verification`, `environment`, `completed_actions`, and `blockers`.

When local CI is used while remote CI is pending, `verification` or `environment` must
also describe the local fallback explicitly: exact commands, result, runtime/toolchain
versions, checkout cleanliness, pending GitHub check name and URL, elapsed wait, and
whether the user explicitly authorized the fallback. Use `local-pass/github-pending` as
the state label. This evidence is supplemental and is never a substitute for a remote
check, deployment, migration, security, or environment-parity result.

Evidence is descriptive, not authority to mutate a repository, database, deployment, or card. On resume, revalidate the head revision and remote/card state. Do not store credentials or unnecessary customer data.

## Failure semantics

- Missing identity, malformed pagination, non-2xx responses, missing required evidence, stale revisions, or malformed reviewer output are errors.
- Empty API results are valid only when the API explicitly proves an empty collection; an error response is never an empty success.
- A dry-run performs reads and local planning only: no merge, push, deployment, migration, PR-body edit, comment, assignment, or column move.
- Uncertain writes require a state read before retry. A matching existing publication/state is reconciled rather than duplicated.

## Safe publication

HTML is serialized with escaping for all untrusted fields. A publication identifies repository, PR/direct revision, card, review cycle, target environment, prerequisites, test identity/role, actions, expected results, regression checks, and relevant failure responses.
