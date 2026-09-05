# Incidents behind the gates

Each gate in `SKILL.md` exists because the softer version failed in production.
Summaries only — the normative behavior is the gate itself.

## Pagination truncation (G2)

A Merge-to-Prod column holding 44 cards read as 15: the skill fetched one
page of `columns/<id>/cards.json` and audited it as the whole column. The
remainder sat unaudited for cycles. Hence: paginate to exhaustion and assert
fetched count equals `X-Total-Count`, or stop as unknown.

## Main→staging drift discovered at merge time (G1)

A promotion PR came up conflicting because `main` held straight-to-main work
the integration branch lacked; the reconcile was hand-resolved across 19
files. Hence: drift check plus an independent temp-worktree merge check
against pinned SHAs, before any audit. `git cherry` alone is not the check —
it is patch-equivalence evidence that misses merge-commit content and
rename resolutions.

## Non-additive migration applied ahead of code (G4)

A text-domain migration reached prod before its writer deploy; the live
writer kept writing the old domain and scoring stalled for 26 hours. Hence:
compatibility/locking/prerequisite/runtime assessment per migration,
`verified_applied` only on object-plus-registry postconditions, and an
ordered deploy/verify/recovery checklist embedded in the PR body. Sequential
steps are never described as atomic.

## Finalize gap: QA-passed card, no detectable commit (G3)

A passed card with no commit match was moved back to QA as "premature". Its
work had shipped in an earlier batch under an unrelated squash name. Moving
a genuinely-shipped, QA-signed card back is costlier than leaving it one
extra cycle. Hence: missing evidence means `unknown`, never `not_ready`.

## Column position treated as proof of shipment

Cards were closed as shipped because they sat in Merge to Prod with a QA
pass comment. The fix had never merged. Hence: the close test is merge-base
ancestry against the owning repo's pinned SHA, nothing softer.
