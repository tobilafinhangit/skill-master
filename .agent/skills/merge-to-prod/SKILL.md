---
name: merge-to-prod
description: Opens or updates a staging→main PR covering all Fizzy cards in the "Merge to Prod" column, audits git vs the column (flags shipped cards for closure and premature cards for move-back), and drafts a terse batched PR title/body. Auto-detects integration/target branches and Fizzy board per repo. Use when a batch of tickets has cleared QA + manual UX testing and is ready to ship to production.
version: 2.0.0
license: MIT
---

# Merge to Prod

> **Note:** This skill references `.claude/rules/*.md` files from the original author's private repos — optional deep-dive context, not required. If those files aren't present in your repo, follow the inline instructions in this skill directly.

Ship a batch of ready-to-prod tickets in one PR. Audit the **Merge to Prod** column against git, surface discrepancies, open or update the staging→main PR.

**Announce at start:** "I'm using the merge-to-prod skill."

**What this skill does NOT do:** it never merges the promotion PR, never deploys, never applies a database migration, never closes a card as shipped without the ancestry and deliverable proof below. Preparation opens or updates a PR. Merging, deploying, and `--finalize` closure are separate, explicitly gated steps.

## When to Use

- Periodically (weekly or on-demand) when tickets have accumulated in the Merge to Prod column
- User says "run the merge to prod workflow", "let's ship what's ready", "merge staging to prod"
- After a QA pass where multiple tickets are marked ready

## Invocation

```
/merge-to-prod              # audit + open/update staging→main PR; asks before Fizzy cleanup
/merge-to-prod --dry-run    # audit only; no PR update, no Fizzy moves, no external writes at all
/merge-to-prod --finalize <PR>  # after the PR has merged: re-validate, then close covered cards
```

`--dry-run` is globally read-only for external systems: no `gh pr create`/`gh pr edit`, no Fizzy `POST` (closure, triage, comments), no migration applies, no deploys. It may run read-only `git fetch`, `gh pr view`, and Fizzy `GET`.

---

## Phase 0: Resolve context and record it (do this first, every run)

**0.1 Read repo instructions before resolving release policy.** If the current checkout has `CLAUDE.md` / `AGENTS.md` / `.claude/rules/working-branch.md` (or the integration-branch equivalent), read them first. Repo instructions override this skill's defaults (branch names, board mapping, deploy rules).

**0.2 Resolve the repository by git remote identity, not directory name.** Directory basenames lie (renamed checkouts, worktrees, sister-repo copies).

```bash
git fetch origin --quiet   # fail closed on error — see 0.6
REMOTE_URL=$(git config --get remote.origin.url)
REPO_TOP=$(git rev-parse --show-toplevel)
```

Match `REMOTE_URL` against the Repo Reference (compare owner + repo slug, ignoring `.git` suffix and `https://` vs `git@` shape). Only fall back to directory-basename matching when no remote is configured, and then say so. If remote identity and directory name disagree, the remote wins and you must surface the conflict.

**0.3 Record the release context and print it.** Every later phase refers to these pinned values — never to a re-resolved "current" branch.

```
repo (remote identity): <owner>/<slug> (+ checkout dir, if different)
integration branch: <name> @ <pinned head SHA>
target branch: <name> @ <pinned base SHA>
Fizzy account / board / Merge-to-Prod column / QA column: <ids>
fetched at: <UTC timestamp>
mode: prepare | --dry-run | --finalize <PR>
```

Pin with exact SHAs: `git rev-parse origin/$STAGING` and `git rev-parse origin/$MAIN` immediately after fetch. Quote both SHAs in the audit output and embed them in the release manifest (Phase 5).

**0.4 Validate overrides before using defaults.** If `.claude/skills/merge-to-prod.json` exists, validate each field (branch exists on `origin`, board/column IDs exist via the Fizzy API) before use. An invalid override is a hard stop — do not silently fall back to auto-detection for that field.

```json
{
  "integrationBranch": "lovable-staging",
  "targetBranch": "main",
  "fizzyBoardId": "03faozjl3gdngcoyzpkr4vf87",
  "mergeToProdColumnId": "03fxshiw308tfj6zkghfb93z0",
  "qaColumnId": "03fdi5xotshcmiuqk8pj24b23"
}
```

**0.5 Unresolved or conflicting identity blocks dependent actions.** If you cannot resolve exactly one repo, one integration branch, one target branch, and one board+column set, stop after printing what resolved and what did not. Do not audit against a guessed pairing.

**0.6 Fail on fetch/ref/command errors.** A failed `git fetch`, an unresolvable ref, a `gh` error, or a Fizzy non-2xx is a stop-and-report, never "no drift" / "column empty" / "already shipped". Empty output after an error means *unknown*, not *clean*.

**Gate G0 (explicit):** context recorded with pinned SHAs, overrides validated (or absent), mode stated. Without G0, no audit, no PR write, no Fizzy write.

> Incident narratives and conditional examples that used to live inline are now in `references/` — `incidents.md` (why each gate exists), `classification-examples.md`, `migration-notes.md`, `scenario-walkthroughs.md`. Gates stay here, beside the step they guard.

---

## Phase 1: Main→Integration drift check (before any audit)

A staging→main PR silently comes up **conflicting** when `main` holds commits the integration branch lacks. Run this **before** Phase 2.

**`git cherry` is patch-equivalence evidence only** — not a conflict detector, not a complete content comparison. A clean `git cherry` (no `+` lines) does **not** prove the merge will be conflict-free: it misses merge-commit content, renames resolved differently on each side, and anything the patch-id comparison cannot see. Treat it as one signal, then run the independent mergeability check below.

```bash
git fetch origin --quiet   # fail closed (0.6)
# '+' lines = commits on main whose patch is NOT on the integration branch.
# '-' lines = already there under a different SHA (benign dual-SHA; ignore).
git cherry "origin/$STAGING" "origin/$MAIN" | grep '^+' | while read _ sha; do
  git log -1 --format='   %h %s' "$sha"
done
```

**Independent mergeability check (pinned revisions, isolated temp environment).** Do not test-merge in the working tree and do not depend on `/tmp` worktrees:

```bash
BASE=$(git rev-parse origin/$MAIN)      # pinned in G0
HEAD=$(git rev-parse origin/$STAGING)   # pinned in G0
WT=".claude/worktrees/mtp-merge-check-<yyyymmdd>"   # repo-local, removed afterwards
git worktree add --detach "$WT" "$BASE"
git -C "$WT" merge --no-commit --no-ff "$HEAD"
MERGE_EXIT=$?
git -C "$WT" merge --abort 2>/dev/null; true
git worktree remove --force "$WT"
```

`MERGE_EXIT != 0` means the promotion PR will conflict regardless of what `git cherry` said. Report the conflicting paths; do not proceed to build the PR until reconciled.

**Record the result in the manifest.** A passing G1 produces the run's `merge_check` record: pinned main SHA, pinned staging SHA, the temp worktree/check identifier, the merge command's exit code, and the explicit status `clean`. `scripts/manifest.py` rejects a manifest with a missing, malformed, stale, or non-clean G1 record — and without a validating manifest nothing publishes (G5) and finalize has nothing to consume.

**If real drift exists → STOP. Do not build the PR yet.** Offer to **reconcile first**: merge `origin/$MAIN` into `$STAGING` in an **isolated worktree** (never the primary tree), with an enumerated list of exactly what the reconcile will pull, and explicit user confirmation. Only continue once both checks are clean. (The *forward* guard lives here; the `hotfix` skill's Phase 5 is the *upstream* fix that merges `main` back into staging right after each hotfix so drift never accumulates.)

**Gate G1 (explicit):** `git cherry` output recorded AND temp-worktree merge check recorded, both against the G0-pinned SHAs, and the clean result stored as the manifest's `merge_check`. A drift finding blocks Phase 2; a missing or failed record fails `manifest.py` validation, which blocks publication and finalize.

---

## Phase 2: Fetch the Merge to Prod column (paginated, asserted)

```bash
git fetch origin --quiet   # fail closed (0.6)

# Fetch ALL cards in the column. Fizzy paginates and returns ONLY page 1
# unless you follow pagination. ALWAYS paginate to exhaustion; never trust
# a single unpaginated fetch.
TMP=$(mktemp); echo "[]" > "$TMP"
page=1
while :; do
  PAGE=$(curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/$BOARD_ID/columns/$MERGE_COL_ID/cards.json?page=$page" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN" \
    -H "User-Agent: skill-master/merge-to-prod")
  N=$(echo "$PAGE" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
  [ "$N" -eq 0 ] && break
  echo "$PAGE" > "$TMP.page"
  python3 -c "import json; a=json.load(open('$TMP')); b=json.load(open('$TMP.page')); json.dump(a+b, open('$TMP','w'))"
  [ "$N" -lt 15 ] && break          # short page = last page
  page=$((page+1))
done
CARDS=$(cat "$TMP"); rm -f "$TMP" "$TMP.page"

# Sanity check: the fetched count MUST equal the column's X-Total-Count header.
TOTAL=$(curl -s -D - -o /dev/null \
  "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/$BOARD_ID/columns/$MERGE_COL_ID/cards.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: skill-master/merge-to-prod" \
  | grep -i '^x-total-count:' | tr -dc '0-9')
echo "Fetched $(echo "$CARDS" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))') of $TOTAL cards in the column."
# If these differ, pagination is broken — STOP and fix before auditing, or you
# will finalize a partial column and leave a silent backlog.
```

A malformed API response, an auth failure, or a count mismatch means the column state is **unknown** — stop, do not audit a partial list. If the column is verified empty: stop. There's nothing to ship.

**Gate G2 (explicit):** fetched count equals `X-Total-Count`, or a named stop with the failure. No partial-column audits.

---

## Phase 3: Inventory the whole release, then classify each card

> **Context budget.** Per-card classification reads the card's body + comments to extract PR refs, then runs git/PR containment checks. Keep that heavy text **out of the parent**: the parent holds only the audit table (`#N → state → evidence`). For columns over ~15 cards, **fan out one subagent per card** (or per wave of ~6) — each reads its own card body+comments + runs the containment checks and returns a compact `{card, state, evidence_refs}` (a PR number, a SHA — not the card text or git output). The shared `BASE`/`HEAD`/change list is computed once in the parent and passed to each child.

### 3.1 Inventory every change between the pinned revisions

```bash
BASE=<G0 base SHA>; HEAD=<G0 head SHA>   # pinned; never re-resolve here
git diff --name-status "$BASE" "$HEAD"
```

This inventory MUST include additions, modifications, deletions, and renames. It is the release you are auditing — the card list is not the release.

### 3.2 Map cards to changes AND every change to readiness evidence

Build two maps and require both:

1. **card → changes**: for each card, the commits/PRs that deliver it (verified per §3.4, not merely matched per §3.3).
2. **change → evidence**: for every change in the §3.1 inventory, the card + readiness evidence that justifies shipping it — or an explicit `unreviewed` flag.

**Never automatically label unmatched work "Infra / chore."** Inspect each unmatched change. If it is genuinely standing infrastructure (CI config, dependency bump with no behavior change, typo fix with its own review), record the evidence that shows it. Otherwise mark it **unreviewed** — it blocks `ready` (see §3.5).

### 3.3 Candidate discovery (signals, not verdicts)

Number, keyword, branch-name, and PR-text matches are **candidate discovery only**. They nominate candidates; they never classify. In particular:

- A commit-message `#N` match is subject to boundary rules: `#12` at end-of-line matches card 12; `312` does not contain card 12; `/12-/`, `/12/`, and `feat/12-` shapes are candidates only after word-boundary checks. Use `scripts/card_refs.py` for extraction — never bare `grep -E "(#$N[^0-9]…)"` as a verdict.
- A card-title keyword hit is a candidate; the deliverable check (§3.4) is the verdict.
- A branch name containing `N` is a candidate; containment of its merge commit is the verdict.

Detection order per card (stop at first **verified** hit, not first candidate hit):

1. **Candidate number match** in `BASE..HEAD` commit messages (word-boundary).
2. **PR-link / QA-signoff containment** *(most reliable — branch- and squash-name-agnostic)* — extract every PR reference from the card body + comments, qualify each by repository, then check each PR's merge commit for ancestry against the pinned SHAs.
3. **Already-on-target search** — repeat against target-branch history (~60 days), then containment-check each hit.
4. **Open PR into staging** whose branch or title references `N`.
5. **Keyword fallback** — 2–3 distinctive title words grepped across branches, then containment-checked.

### 3.4 Verification (what turns a candidate into a state)

- **Retain repository-qualified PR identities.** A PR reference is `(repo, number)`. Never resolve a cross-repository URL (`github.com/<other>/pull/NNN`, a Congrats PR cited on a Vetted card) as a local PR number. A bare `#NNN` inherits the card's owning repo only after you have determined that owner from the QA-signoff branch — it is never assumed to be the current checkout's repo.
- **Verify the association using explicit card references AND the actual deliverable.** The card (body or comments) must explicitly reference the PR/branch/commit, AND the PR's title/body must name the card (`fix(#N)` / `Fizzy #N` — title-verify before trusting any PR number), AND the PR's merge commit must be contained where the state claims. A title match alone is insufficient in both directions.
- **Account for all required PRs/repositories and any later revert or superseding change.** A multi-PR ticket with one PR unmerged is not covered. A merged fix later reverted is not covered — the revert must be detected (`git log --oneline BASE..HEAD --grep='Revert.*#N'` plus PR state) and the card re-evidenced. A superseded PR (closed in favor of another) counts only via the PR that actually merged.
- **Sister-repository evidence may be inspected, but cleanup stays scoped.** You may `cd` into a sister checkout (or query its history) to verify a sister-repo card's deliverable. You must NOT close, move, or comment on cards outside this invocation's resolved board ownership — report them, leave them.

### 3.5 Mutually exclusive states and the release verdict

Each card ends in exactly one state:

| State | Meaning |
|---|---|
| `covered` | Verified deliverable merged into the integration head (`HEAD`), will ship in this batch. Not yet on target. |
| `already_on_target` | Verified deliverable is an ancestor of the target base (`BASE`) — shipped in a prior batch, via a differently-named branch, or otherwise already live. Flag for closure. |
| `not_ready` | Verified NOT shippable: an open PR into staging not yet merged, a missing deliverable, a revert without re-land — established by positive evidence, never by "no matches found". Flag for move-back to QA. |
| `unknown` | Missing evidence. Includes QA-passed cards with no detectable commit (almost always a finalize gap, not missing work) — never move these back silently; surface for a human decision. |
| `non_code_complete` | No code change required AND explicit completion evidence exists (linked QA full-pass, completed manual task, recorded decision). Must never be described as "in main" — there is no commit to be in main. |

Rules:

- **Missing evidence means `unknown`.** Absence of search matches does not prove `not_ready`.
- **The close test is merge-base ancestry, nothing softer.** `covered`/`already_on_target` require `git merge-base --is-ancestor <mergeCommit> <pinned-SHA>` run against the repo that owns the fix. Column position, QA comments, `[FIXED]` titles, and rule files are not proof — they mean queued / verified / pattern-learned, not delivered.
- **Release verdict** over the whole inventory: `ready` | `blocked` | `incomplete`.
  - `ready`: every change in §3.1 maps to `covered`/`already_on_target`/`non_code_complete` with verified evidence, and every card maps to a state with evidence. Only then may a promotion PR be created/updated.
  - `blocked`: any card is `not_ready`, any change is `unreviewed`, or any gate failed. Print the proposed PR content AND the blockers; do **not** create or update the promotion PR.
  - `incomplete`: any card is `unknown` or any evidence is missing/partial. Same handling as `blocked`: print, do not publish.
- **Excluded work on staging → hand off to selective-release workflow.** If staging carries work that must not ship yet, stop this run as `blocked` (excluded work present) and hand off to `selective-staging-merge` 2.0. That workflow must pin fresh source/base revisions, inventory every release unit, validate evidence and dependencies, reconstruct once in an owned worktree, and re-verify immediately before any separately authorized publication. Do not improvise cherry-picks or reuse a prior held-back commit list here.
- **Revalidate before publication.** Immediately before creating/updating the promotion PR, re-fetch `origin/$STAGING` and `origin/$MAIN`. If either moved since G0, re-pin, refresh every affected evidence item (drift check, inventory, containment), and re-print the audit. Never publish from stale pins.

**Gate G3 (explicit):** the two maps (§3.2) printed with every change accounted for, every card in exactly one state, release verdict stated. `blocked`/`incomplete` never publishes. Revalidation recorded when pins moved.

Worked examples live in `references/classification-examples.md`. Scenario walkthroughs for judgment-only cases live in `references/scenario-walkthroughs.md` — they illustrate expected outcomes; they do not substitute for running the checks.

---

## Phase 4: Migration and runtime assessment (only if `supabase/migrations/` exists)

This skill ships *code* to `main` but never applies a DB *migration* to prod. A migration in the batch therefore reaches prod-code with **no prod-DB change applied** — surfacing it here is load-bearing. Read `references/migration-notes.md` for the incident behind this phase.

Skip entirely if the repo has no `supabase/migrations/` (root or one level deep). Auto-detect the prod ref from the Repo Reference; if unknown, ask — never guess a ref.

**4.1 Enumerate from the pinned release revision, preserving change status.**

```bash
git diff --name-status "$BASE" "$HEAD" -- 'supabase/migrations/*.sql' 2>/dev/null
# (also check a one-level-deep path, e.g. congrats/supabase/migrations/, per repo layout)
```

Review the file **contents at `HEAD`**. Additionally flag any historical migration (already on target) whose content was **modified or deleted** between `BASE` and `HEAD` — that is never routine; it requires explicit investigation before anything publishes. If none in the delta and none modified → print "No migrations in this batch" and continue.

**4.2 Assess compatibility — no blanket additive-safety guarantees.** "Additive" does not mean "safe". For each migration assess and record: **compatibility** (does old code run against the new schema AND does new code run if the migration is not yet applied?), **locking** (will it take an `ACCESS EXCLUSIVE` lock on a hot table? full-table rewrite?), **prerequisites** (extensions, roles, prior migrations), and **affected runtime** (which edge functions, crons, or clients read/write the touched objects). When unsure, assume coupled (fail safe). The tell is "does an already-live writer's behavior change the instant this lands?" — if yes, it's coupled.

**4.3 Record migration state with all postconditions.** Read-only checks against the **prod** ref via SQL (`information_schema`, `to_regclass`, `pg_proc` + new-marker, `supabase_migrations.schema_migrations` registry):

| State | Postconditions (ALL required) |
|---|---|
| `verified_applied` | Key object present on prod AND registry row for the migration version present. Object alone is not enough; registry alone is not enough. |
| `missing` | Key object absent AND registry row absent. |
| `partial_or_drifted` | Object present but registry absent (hand-applied?), registry present but object absent (failed/rolled-back apply?), or object present with a different definition than `HEAD` content. Treat as blocked until reconciled. |
| `unknown` | Checks could not run (no access, error, ambiguous key object). Blocks `ready` the same as `partial_or_drifted`. |

For `CREATE OR REPLACE` function changes, "present" means the **new body** (match on a marker only the new version contains), not the old one.

**4.4 Coupled changes get an ordered deploy/verify/recovery checklist — never "atomic".** Sequential database and runtime operations are not truly atomic; do not describe them that way. Each coupled pair gets: ordered steps (migration step + code/deploy step in dependency order), a verification query per step, and a recovery action per step (what to run if that step fails after the previous one succeeded). **Embed this checklist directly in the PR body** (Phase 5 template) so it is visible at merge time.

Apply via the Dashboard SQL editor in filename order at go-live. Never `supabase db push` (files may have been edited after first apply).

Guardrails:

- **Read-only here.** This phase classifies and reports; it applies nothing. Early pre-apply for rehearsal is a separate, user-initiated step under its own rule, never an automatic side effect.
- **The prod ref is per-repo** — never hardcode one repo's ref for another.
- This is the *prod* side at promotion time; it does not replace staging-side QA migration checks.

**Gate G4 (explicit):** every delta migration listed with its assessment + state, checklist embedded in the PR template when coupled work exists. `partial_or_drifted`/`unknown` force the release verdict to `blocked`/`incomplete`.

---

## Phase 5: Publish the promotion PR (only on `ready`)

### 5.1 Manifest: the versioned record of what was evidenced

Define one JSON release manifest per run (schema `mtp-manifest/2.0`). It contains: repository identity (remote URL + resolved slug), pinned `BASE`/`HEAD` SHAs + fetch timestamps, per-card entries (number, state, validated deliverables with repo-qualified PR refs + merge SHAs, readiness evidence), the full §3.1 change inventory with per-change evidence or `unreviewed` flags, migration/runtime requirements with states, and blockers. Validate with `scripts/manifest.py` before publishing — it exits non-zero on any schema or state violation.

The manifest **records evidence; it is not trusted merely because it exists in a PR.** Every consumer (this skill's finalize, any human, any other tool) re-validates the manifest AND the live state it points to. A manifest copied from another run, hand-edited, or pointing at moved pins is rejected and the evidence is rebuilt.

### 5.2 Managed PR-body section (machine-owned, human-respecting)

Store the manifest and all generated content inside a clearly delimited managed section of the PR body. Everything outside the markers belongs to the operator and must be preserved across updates (use `scripts/managed_section.py` — never string-concatenate a new body over the old one):

```markdown
<!-- merge-to-prod:managed:begin -->
## Staging → Prod batch (YYYY-MM-DD)

Merging N tickets from the **Merge to Prod** column of the {Board Name} board.

Base: <BASE SHA> · Head: <HEAD SHA> · Verdict: ready

### Tickets
- #<num> [Title](https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/<num>) — one-line note + evidence (PR repo#num @ sha, state)
- …

### Unmatched changes
- <one-line per §3.1 change with its evidence; unreviewed items never appear here — they block instead>

### Migration / go-live checklist
- <each not-on-prod migration with its §4 state + ordered steps + verification + recovery; raw DDL linked, not pasted, when long>

<!-- merge-to-prod:manifest version="2.0" -->
```json
{ …manifest… }
```
<!-- merge-to-prod:managed:end -->
```

Operator notes, reviewer checklists, and any headings outside these markers survive every update. On a body whose managed section was hand-edited (markers present but content divergent), treat the manifest as suspect: re-validate, rebuild if it fails, and say so.

### 5.3 Create or update

```bash
EXISTING=$(gh pr list --base $MAIN --head $STAGING --state open --json number -q '.[0].number')
```

- If `EXISTING` set → `gh pr edit $EXISTING` replacing only the managed section.
- Else → `gh pr create --base $MAIN --head $STAGING --title "$TITLE" --body "$BODY"`.
- Title: `chore: merge to prod — YYYY-MM-DD batch (N tickets)`. Keep it terse — no filler prose.
- On `--dry-run`: print the title + body and the exact command that would run. Execute nothing.

**Gate G5 (explicit):** verdict is `ready`, pins revalidated fresh, manifest validates (including its G1 `merge_check` record), managed-section replace used. Otherwise print-and-stop per §3.5.

---

## Phase 6: Fizzy triage of already-decided cards (ask first)

This phase moves only cards the audit already decided. It re-decides nothing.

Show the planned actions and pause for confirmation. **Reuse the existing user authorization** from the confirm step — if the user already authorized "close already-shipped + move back premature for this batch", do not ask twice. **Request missing authorization only after preparing the concrete action list** (never a bare "can I touch Fizzy?"):

```
Planned Fizzy actions (batch YYYY-MM-DD, BASE <sha> HEAD <sha>):
  - Close (already_on_target, verified): #A, #B, #C
  - Move back to "QA to be confirmed" (not_ready, verified): #X, #Y
  - Leave in place (covered, shipping in this PR): #1, #2, #3
  - Needs human (unknown / non_code_complete without evidence): #U… (no action proposed)
```

`unknown` cards are never auto-moved. `non_code_complete` cards close only with their explicit completion evidence cited in the close comment.

On confirmation:

**Close shipped cards** — a **state change**, not a column move:

```bash
# Fizzy "Done" is card closure. There is no "Done" column with a column_id.
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/<N>/closure.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN"
# 204 = success — then READ BACK the card and assert closed before reporting it
```

**Move premature cards back to QA to be Confirmed:**

```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/<N>/triage.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"column_id\": \"$QA_COLUMN_ID\"}"
# 204 = success — then READ BACK the card and assert the new column
```

**Post a comment on each moved-back card** explaining why (HTML, Fizzy-friendly):

```bash
curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/<N>/comments.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": {"body": "<p>Moved back from <b>Merge to Prod</b> during the YYYY-MM-DD batch (PR #NNN). PR #MMM is still open — code is not in integration branch yet. Re-test once merged.</p>"}}'
```

**Check every mutation response and read back resulting state** (the `scripts/fizzy-file-card` create→triage→verify pattern applies to closes and moves too). After an uncertain write (timeout, ambiguous status, connection reset), **reconcile before retrying**: read the current card state; only retry the write if the read shows it did not land. Never retry blindly — a timed-out close that actually landed must not become a double-close + confused report.

Leave **covered** cards in Merge to Prod — they stay until the PR actually merges. Use `--finalize` later.

---

## Phase 7: Finalize (separate invocation, after merge)

`/merge-to-prod --finalize <PR_NUMBER>` runs after the promotion PR merged to main. It re-validates everything — the manifest is a starting pointer, never the proof.

```bash
# 1. Verify the PR is merged, in the resolved repo, on the expected branches
gh pr view $PR_NUMBER --json state,mergedAt,baseRefName,headRefName,mergeCommit,repository \
  --jq '{state, base: .baseRefName, head: .headRefName, sha: .mergeCommit.oid}'
# Expect: state MERGED, base == target branch, head == integration branch.
# If OPEN (or wrong repo/branches), stop.
MERGED_SHA=<mergeCommit.oid>   # the actual revision that landed — evidence re-anchors here
```

```bash
# 2. Extract candidate ticket numbers — ONLY from bullet lines under "### Tickets"
#    INSIDE the managed section. Never from the whole body: GitHub PR numbers
#    like (#541), parenthetical refs like "Card #644", and related-ticket refs
#    like "(from #318)" all false-positive under whole-body extraction.
#    Use scripts/card_refs.py (bounded, word-boundary, repo-aware). There is
#    no awk fallback — whole-body grep/awk extraction is banned because it
#    false-positives on the refs named above:
TICKETS=$(gh pr view $PR_NUMBER --json body -q .body \
  | python3 scripts/card_refs.py --stdin)
```

```bash
# 3. For EACH candidate: re-read current card state, re-validate deliverable
#    containment against MERGED_SHA (not the pre-merge HEAD pin), and confirm
#    required deployment/migration evidence where the manifest requires it.
#    New conflicting evidence (card reopened, revert landed after the merge,
#    migration still missing on prod) BLOCKS that card — it is skipped, not closed.
```

```bash
# 4. Legacy PRs without a manifest: reconstruct and validate the evidence from
#    scratch (pins → inventory → containment → migration states). Never close
#    from Markdown ticket-number extraction alone.
```

```bash
# 5. Close each validated card; check the mutation response AND read back state.
for N in $TICKETS; do
  curl -s -X POST "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/cards/$N/closure.json" \
    -H "Authorization: Bearer $FIZZY_API_TOKEN"
  # assert HTTP 204, then GET the card and assert closed before counting it
done
```

Confirm with a separated summary — **never report blanket success after partial failure**:

```
Finalize complete for PR #NNN (merged <sha>):
  Closed (validated): #A, #B
  Skipped (blocked, reason per card): #X (revert landed after merge), #Y (migration still missing on prod)
  Blocked (needs human): #U (conflicting evidence — <what>)
```

---

## Confirmation Message (end of Phase 6)

```
Merge to Prod — done for this batch

PR: #<NNN> — {title}
  Status: OPEN, awaiting review (preparation only — not merged, not deployed)

Context: <owner>/<slug> · <staging>@<HEAD sha> → <main>@<BASE sha>
Verdict: ready | blocked | incomplete (+ manifest version)

Shipping (N cards, stay in Merge to Prod):
  #1, #2, …

Closed (already_on_target, N cards):
  #A, #B, …

Moved back to QA to be confirmed (N cards):
  #X, #Y — reason per card

Needs human (unknown, N cards):
  #U… — what evidence is missing

Next: after PR merges, run `/merge-to-prod --finalize <NNN>` to re-validate and close the shipping cards.
```

---

## Helper scripts (in `scripts/`, stdlib Python only)

| Script | Purpose |
|---|---|
| `scripts/manifest.py` | Validate (and scaffold) the `mtp-manifest/2.0` JSON: required fields, SHA shape, state enums, per-change evidence completeness. Used before publish and during finalize. |
| `scripts/card_refs.py` | Bounded card-reference extraction: managed-section scope, bullet-line anchor, word-boundary numbers (`#12` ≠ `312`), repo-qualified PR identities. Used by finalize; also usable to audit Phase 3 candidates. |
| `scripts/managed_section.py` | Extract/replace the `merge-to-prod:managed` PR-body section while preserving operator content outside the markers; detects hand-edited and legacy (markerless) bodies. |

These are narrow parsing/validation helpers, not a release runner — the workflow decisions stay in this skill. Reused patterns (not duplicated code): `verifying-apis` manifest-driven stdlib validation; `fizzy-file-card` mutate→check-response→read-back; `selective-staging-merge` is the separate workflow to recommend when staging carries excluded work — do not re-implement cherry-picks here.

---

## Fizzy API Reminders

- Always `.json` suffix on action endpoints (closure, triage, comments, assignments) — missing suffix returns 422 or 401
- **"Done" is card closure** — `POST /cards/<N>/closure.json` — NOT a column move. Fizzy's default "Done" bucket is a status field, not a column with an ID.
- Mutations return `204 No Content` on success; creations return `201 Created`. Assert the status, then read back the card — a bare 2xx without readback is not proof.
- Token lives in `.env.local` as `$FIZZY_API_TOKEN`. Never hardcode.
- Comment body is HTML — markdown is ignored and renders as a blob
- Card body field is `description`, comment body field is `body` (they differ)
- **Column listings paginate with an escalating page size (15→30→50…).** `GET .../cards.json` returns only the first page unless you follow `Link: rel="next"` / `?page=N`. The response carries `X-Total-Count`. Any column listing MUST loop pages to exhaustion and assert the fetched count equals `X-Total-Count` — never stop on the first <15 page; a single fetch silently truncates a >15-card column. Use the per-column endpoint — `cards.json?board_id=` is silently ignored. Full rules: "Reading a Board — AUTHORITATIVE" in `/fizzy`.
- **Column membership ≠ this repo.** A board's Merge-to-Prod column can hold cards whose work ships via sister repos. Detect the owning repo per card via its QA-signoff branch name (`lovable-staging`=Vetted, `verify-deployments`=Congrats, `backend-verify-deployment`=backend) and qualify every PR identity by repo before classifying; never judge a sister-repo card against this repo's git, and never close or move it from an invocation scoped to another repo.
- **Title-verify before trusting a PR number.** Card numbers and PR numbers collide across repos and a comment often cites *another* ticket's PR. Confirm the candidate PR's title names the ticket (`fix(#N)`/`Fizzy #N`) before using its merge commit as proof-of-ship.

---

## Repo Reference

Primary resolution is git remote identity (Phase 0). The directory-name table below is a fallback hint only:

| Repo directory name | Integration branch | Target branch | Board |
|---|---|---|---|
| `vettedai-audition-supabase-version` | `lovable-staging` | `main` | Vetted |
| `vetted-congrats-Flow-GENEROUS` | `verify-deployments` | `main` | Congrats |
| `backend-restructing` | `backend-verify-deployment` | `main` | Congrats (shared) |

If no match: ask the user.

---

## Board Reference

Used by Phase 0 to derive column IDs from the board.

| Board | Board ID | Merge to Prod Column ID | QA to be Confirmed Column ID |
|---|---|---|---|
| Vetted | `03faozjl3gdngcoyzpkr4vf87` | `03fxshiw308tfj6zkghfb93z0` | `03fdi5xotshcmiuqk8pj24b23` |
| Congrats | `03f58rc5c48jorujpxqp5da5b` | *(lookup by name on first run)* | `03f58rxrkofln7o86yce47gvk` |
| Bugs | `03fl735hqcd0h1pettl8o94oo` | *(lookup by name on first run)* | `03fnl3h1becpuazzhahxbn208` |

**Lookup by name** (fallback when column ID not known):

```bash
curl -s "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/$BOARD_ID/columns.json" \
  -H "Authorization: Bearer $FIZZY_API_TOKEN" \
  | python3 -c "import json,sys; [print(c['id']) for c in json.load(sys.stdin) if c['name'].lower()=='merge to prod']"
```

When a new board's Merge to Prod column ID is discovered, add it to this table (edit this file + commit + distribute).

---

## Team Reference

| Person | Role | User ID |
|--------|------|---------|
| Tobi Lafinhan | Owner | `03f58r3y17c4p4ucpvaf7mn5g` |
| Elvis Muchiri | QA Lead | `03fcio1h8spstjpkc82vciugk` |
