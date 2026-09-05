# Classification examples

Candidate discovery nominates; verification decides. Each example shows the
candidate signal and the verification that must follow.

## Boundary: card 12 vs 312 vs #123

- Commit `fix: retry backoff (#12)` at end of line: candidate for card 12.
  Verify: card body references the PR/branch AND the merge commit is
  contained at the pinned SHA. Then classify.
- Commit `fix: latency budget 312ms`: NOT a candidate for card 12 (no `#`
  prefix, no boundary). Ignore for card 12.
- Commit `fix: onboarding (#123)`: NOT a candidate for card 12 (digits
  continue). `scripts/card_refs.py` enforces this; bare grep does not.

## Cross-repository PR-number collision

Card 45 (Vetted board) cites "PR #45" in a comment, but the comment thread
also links `github.com/<congrats-repo>/pull/45`. The URL keeps its own repo
identity — it is never resolved as Vetted PR 45. Verify the Vetted-side PR
whose title names card 45, then check its merge commit. If only the
Congrats PR exists, the card's deliverable is unverified (`unknown`), not
premature.

## Multi-PR ticket, one deliverable missing

Card 78 lists PRs 101 (merged to staging) and 102 (still open). PR 101
alone does not cover the card: all required PRs must be verified. State is
`not_ready` by positive evidence (open PR 102), flagged for move-back.

## Reverted fix

Card 90's fix merged via PR 110, then PR 111 `Revert "fix #90"` merged on
top. The card is not covered until a re-land merges. `mentions_revert`
flags the pattern; the agent re-evidences against the current head.

## No-code completion

Card 64 is a manual QA task with a linked full-pass and no PR. With explicit
completion evidence it closes as `non_code_complete` — recorded as
completed work, never described as "in main".
