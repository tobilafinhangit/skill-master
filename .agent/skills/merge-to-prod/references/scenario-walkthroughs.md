# Scenario walkthroughs (prose-only requirements)

Text-search assertions cannot prove workflow correctness for behavior that
only manifests against live git, network, or timing states. For those cases
this file gives the scenario, the expected agent behavior, and the expected
outcome. Reviewers: walk the scenario, do not grep for it.

## 1. Changed release head after audit

Setup: audit completes against HEAD `aaa…`; before publication, `origin`
staging advances to `bbb…` (new push lands). Expected: the agent re-fetches,
detects the pin move via `pins_match`, re-runs the drift check, inventory,
and every containment that could be affected, then re-prints the audit. It
never publishes from the `aaa…` evidence. `tests` assert `pins_match`
returns False on moved pins; the refresh discipline itself is prose.

## 2. Positive patch drift with a clean merge

Setup: `git cherry` shows two `+` lines (real drift), yet the temp-worktree
merge check exits 0. Expected: the agent still stops — drift means the
promotion PR would drag unintended main-side work into the batch
description, or the reconcile is missing. Clean mergeability does not clear
unreconciled drift. Both signals are recorded; either one blocks.

## 3. Merge-only content missed by patch comparison

Setup: `git cherry` is clean (no `+`), but the temp-worktree merge check
conflicts on a path both sides renamed. Expected: the agent reports the
conflicting paths and stops. This is the case `git cherry` cannot see, and
the reason the skill requires both checks. Expected outcome: reconcile
first, then re-audit.

## 4. Failed/malformed API response and incomplete pagination

Setup (offline fixture `pagination_short.json` + `pagination_mismatch.json`):
page 2 returns malformed JSON; separately, fetched 30 of `X-Total-Count: 44`.
Expected: both are stops with a named failure, never a partial-column
audit. Unit tests assert the malformed body raises and the count comparison
fails; the "do not proceed" behavior is prose.

## 5. Closure timeout followed by readback showing success

Setup: `POST …/closure.json` for card A times out; immediate `GET` shows
card A closed. Expected: the agent records the close as landed, does NOT
retry the POST, and reports card A under Closed with a note
("close confirmed on readback after timeout"). Blind retry risks double
side-effects and confused reporting. The reconcile-before-retry rule is
prose; no unit test can execute the timeout.

## 6. Dry-run attempting an external mutation

Setup: a planned command list includes `gh pr edit 12 --title …` alongside
reads. Expected: `--dry-run` refuses to execute anything and reports the
violation naming the offending command. Unit tests assert `find_mutations`
flags the list; the "execute nothing" enforcement is prose plus the
G5 gate.
