---
name: engineering-pulse
description: Cross-repo engineering productivity analysis with bounty estimation. Use when the user wants contributor stats, PR velocity, workload distribution, team performance snapshots, or bounty payout projections.
version: 3.16.0
license: MIT
metadata:
  author: VettedAI
  category: engineering-management
  tags: [productivity, performance-review, team-health, velocity, delegation, bounty]
  created: 2026-03-11
  updated: 2026-10-02
argument-hint: "[weekly|monthly|quarterly] [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--pre-invoice] [--payout-json] [--draft|--payout]"
---

# Engineering Pulse — Contributor Productivity & Bounty Analysis

Generates a cross-repo contributor analysis from merged PR data with bounty payout estimates. Designed for weekly standups, monthly reviews, quarterly performance cycles, delegation planning, and bounty reconciliation.

> **Philosophy:** Deflation bias. This is an AI-assisted workflow — agents write most of the code, engineers supervise and validate. We pay for judgment and output, not volume. When in doubt, the lower tier wins.

## Context budget — the heavy data stays in the script, never the conversation

This skill pulls O(N) raw data: `gh pr list` (up to 500 PRs/repo across several repos), a `gh pr view` per above-S-tier PR, and the ~800-card Fizzy comment scan (paginated to exhaustion). If that raw JSON lands in the **agent's** context window, the run bloats and can crash — and unlike a script's process memory, text in the conversation is billed every turn for the rest of the run and can't be evicted.

The rule: **the self-contained Python script is where all that data lives.** It shells out to `gh`/Fizzy, holds the PR JSON and comment threads in its own memory, and prints **only the finished report tables**. The agent context should only ever hold the script and its final markdown output — never raw `gh pr list` / `gh pr view` / `/comments.json` payloads. This is the engineering-pulse analogue of the per-card subagent fan-out the bulk Fizzy skills use: a disposable worker (here, the script process) absorbs the heavy text and returns a compact result.

Concretely:
- Do **not** run `gh pr list …` / `gh pr view …` / Fizzy fetches as standalone Bash calls whose JSON streams back into the conversation. Let the script do the fetching in-process and emit only tables.
- If you must debug a raw pull interactively, **redirect to a file** (`gh pr list … > /tmp/ep_prs.json`) and inspect with `jq` + a few rows — never cat the whole array into the reply (same discipline as the `supabase-data-access` rule).
- The `gh pr view` per-PR fan-out (Step 2) and the 800-card comment scan (Step 8 ops detection) are the two biggest sources — both are already designed to run inside the script's `ThreadPoolExecutor`; keep them there.
- Verify with `submodules/skill-master/scripts/measure-skill-run.ts` — **parent peak context** should stay flat run-to-run regardless of how many repos/cards are scanned, because the volume lives in the script, not the conversation. A parent peak that grows with batch size means raw data is leaking into context.

## When to Use

- Weekly: quick velocity check — who shipped, who's blocked?
- Monthly: workload balance + bounty payout preview
- Quarterly: performance review input — PR volume, scope, growth trajectory
- Ad-hoc: "who could take on more?" or "who needs clearer task assignments?"
- Bounty reconciliation: "what does each dev earn this period?"
- Explicitly via `/engineering-pulse`

## Repos to Analyze

The repo list is **config-driven** — read it from `repos.yaml` next to this SKILL.md. Each entry has `name`, `path`, and `integration_branches`. Adding a new repo is a single YAML append; no skill code changes.

```yaml
# repos.yaml
repos:
  - name: audition
    path: /Users/USER/code/repos/vettedai-audition-supabase-version
    integration_branches: [main, lovable-staging]
  - name: nts
    path: /Users/USER/code/repos/nts-event-platform-supabase
    integration_branches: [main, staging]
  # ... append more here
```

**Target branches:** Only count PRs merged into one of the per-repo `integration_branches`. PRs between feature branches are excluded. Each repo can have its own integration branch (e.g., `lovable-staging` for audition, `verify-deployments` for congrats, `staging` for nts).

If a repo path doesn't exist on disk or `gh` returns auth errors for it, log a warning and continue with the remaining repos — never block the whole report on one missing repo.

### Repo-allowlist drift check (run every report — the sustainable scaling mechanism)

Auto-discovery across "everywhere an engineer works" is impossible by construction: from the founder's `gh` only his orgs (`Generous-Circle`, `congratsai`, `Vetted-AI`) + his own repos are visible — engineers' personal repos are not. So `repos.yaml` is a **curated allowlist, never auto-inclusion.** Make curation cheap: each run, enumerate org repos pushed within the window, diff against the allowlist, and emit a **"new repos not in allowlist → project or ignore?"** prompt for the manager (~30-second monthly triage):

```bash
for org in Generous-Circle congratsai Vetted-AI; do
  gh repo list "$org" --limit 100 --json nameWithOwner,pushedAt \
    --jq ".[] | select(.pushedAt >= \"$WINDOW_START\") | .nameWithOwner"
done   # diff against repos.yaml; anything new → ASK, never auto-add
```

Fails safe: an unknown repo is flagged + **not measured**, never silently counted. Personal-owned project work (e.g. Elvis's automation code, currently on a personal repo) is measured via its Fizzy board (the `qa-automation` board in `ops-rates.yaml`), or moved into an org to become visible — never crawled. Known parked/dormant repos to keep ignoring: `Vetted-AI/recruiters-ring` (sole PR by `nzommmo`, off roster), `Generous-Circle/GC-Back` (dormant).

**Known gap, not yet built — cross-repo shared-history dedup.** `Vetted-AI/vetted-gtm-frontend` was seeded from `vetted-gtm` and shares its git history; Joy's July figure double-counted ~5,000 KES of identical commits (same titles/dates: Apify pipeline, scrape-job API, auth layer) appearing in both repos before this was caught by hand (reports/engineering-pulse/2026-07-payout.md Addendum 3, second one). The fix applied then was "add gtm-frontend to repos.yaml so it flows through the pipeline" — but no actual same-title/same-date cross-repo dedup step exists in this skill today; the July fix only removed the symptom (a hand-added number outside the normal pipeline), not the underlying risk (two allowlisted repos sharing git ancestry). Currently dormant (both repos show 0 commits most months) but not actually guarded — if either becomes active again, re-derive this check (compare commit subject+date across any two repos known to share a fork/seed relationship) rather than assuming the July fix covers it.

### Board-allowlist drift check (run every report — the Fizzy-side mirror of the repo check above)

`ops-rates.yaml`'s `boards` list is the same kind of curated allowlist as `repos.yaml`, with the same failure mode: a board that exists and has real engineer activity on it, but was never added, is invisible — not flagged, not "not measured," just silently absent from every report with no error. Unlike the repo check, there is currently **no automated enumeration step** for this — it has to be run manually:

```bash
curl -s "$FIZZY_BASE/boards.json" -H "Authorization: Bearer $FIZZY_API_TOKEN" -H "User-Agent: VettedAI/1.0" \
  | python3 -c "import json,sys; [print(b['id'],'|',b['name']) for b in json.load(sys.stdin)]"
# diff the full list against ops-rates.yaml's `boards:` entries — anything missing → ASK, never silently skip
```

**Why this is mandatory, not a one-time fix:** September 2026, Tobi's own read of Gaudensia Akinyi's number ("this looks light, she does engineering-operations work") caught what this check would have: the `engineering-operations` board (`03gggxqayxmjl6pjdleq7nijn`) was never in `ops-rates.yaml` — not even in the "deliberately not scanned" exclusion note, meaning it wasn't a considered decision, just a gap nobody noticed because a missing board produces no error, no warning, nothing. It held two substantial September security audits (14,327 and 9,396 characters, 4,000 KES combined under the new `ops-deliverable` category) that had been completely invisible. The `copilot` board (`03gplllzjyj0acg8vy1882dm7`) was found the same way and added alongside it.

**How to apply:** run the enumeration above at least once a quarter, or immediately whenever a manager's own read of someone's output ("this seems low for what I know they did") disagrees with the report — that disagreement is itself the signal, exactly as it was here. A repo-allowlist-style drift check only covers code; it was never going to catch a Fizzy-only workstream like a scoping/audit board. Both allowlists need their own periodic check, not just one.

**Known gap, not yet built — multiple independently-scoped tickets consolidated into one PR.** When stacked-branch/rebase conflicts force several separately-groomed tickets to land as a single merged PR (not one ticket split into many, the *opposite* direction from `split-suspect`), the correct price is the SUM of what each constituent ticket would earn on its own, not one tier based on the merged diff's aggregate size (reports/engineering-pulse/2026-07-payout.md Addendum 9 — Liban's #1464 was 5 independently-scoped tickets #1926-1931, priced as one L-tier 2,000 KES deliverable until retiered per-ticket, +4,500 KES owed). There is no structural detector for this today — the current session's work only built detectors for the inverse case (one ticket inflated into many PRs). A PR whose body or commit history references multiple distinct Fizzy ticket numbers with substantial, non-overlapping diffs per ticket is the signal to watch for and retier manually until a structural check exists.

### No-silent-zero rule (coverage honesty)

Until a coverage gap is closed, the report MUST print an explicit **"not measured"** line for that surface/person rather than implying a zero. A silent zero reads as "did nothing"; it usually means "we didn't look there." Concretely this covers: engineers with a missing `fizzy_user_id` (Liban, wizzfi1 — ops undetected), repos flagged by the drift check, and dormant/un-scanned boards. When a number looks shockingly low, suspect coverage before performance.

## Step 1: Determine Time Window

Parse the user's argument to set the analysis window:

| Argument | `--since` | `--until` |
|----------|-----------|-----------|
| `weekly` | 7 days ago | today |
| `monthly` | 30 days ago | today |
| `quarterly` | 90 days ago | today |
| `--since 2026-01-01` | 2026-01-01 | today |
| `--since 2026-01-01 --until 2026-02-28` | 2026-01-01 | 2026-02-28 |
| *(no argument)* | all time | today |

## Step 2: Pull Merged PR Data

For each repo, run via `gh` CLI:

```bash
gh pr list --state merged --limit 500 \
  --json number,title,author,createdAt,mergedAt,additions,deletions,changedFiles,labels
```

**Additional data for flagging (PRs above S-tier):** For PRs with changedFiles > 3 OR (additions+deletions) > 100, also fetch:
```bash
gh pr view {number} --json files,reviews,commits
```
This enables revert detection, file-path analysis, and review tracking.

**If a repo returns a 502 error** (GitHub GraphQL overload), retry once without the `body` field and with `--limit 200`. If it still fails, note it and proceed with available data.

**Filter by time window:** After fetching, filter PRs where `mergedAt` falls within the `--since` / `--until` range.

**Exclude bots:** Filter out authors where `is_bot: true` or login matches: `dependabot`, `renovate`, `github-actions`, `lovable-dev`.

**Exclude founder:** `tobilafinhangit` is tracked in a separate "Founder Activity" section — not included in the bounty table. Founder output is sweat equity, not bounty-eligible.

### Step 2b: `source: git-log` repos (no GitHub PRs)

Some repos have `source: git-log` in `repos.yaml` — they have **no GitHub PRs** (`gh pr list` returns `[]`) because work is squash-pushed straight to the integration branch (e.g. Joy's `vetted-gtm`, personal repo, direct-to-`main`). For these repos, **do not** call `gh pr list`; instead derive one **PR-equivalent per non-merge commit** on the integration branch:

**Fetch before you log — mandatory, every run.** A local clone of a `git-log` repo is not kept current by anything else in this skill or in normal workflow — unlike `gh-pr` repos (where GitHub's API is always the live source of truth), these repos are read from **whatever commit the local clone happens to be sitting at**. A stale clone doesn't error — `git log` against it just silently returns fewer commits, with no signal that anything is wrong. Always run `git -C <repo.path> fetch origin <integration_branch> --quiet` immediately before the `git log` pull below, and read from `origin/<integration_branch>`, not the local branch ref.

**Why this is mandatory, not a nice-to-have:** September 2026 payout run, Wisdom Shaibu's `manual-qa` repo. The local clone was **213 commits behind** `origin/master` at the time `git log` ran, with no fetch step in between — it read master as the clone understood it, which was weeks stale. This made his September code output look like 1 commit / 500 KES, when his real output (confirmed after `git fetch` + `git log origin/master`) was **30 commits across 8 tickets, 8,000 KES** — a 16x undercount. The repo isn't being watched or polled by anything; a local clone that was fresh when first set up just quietly rots.

```bash
git -C <repo.path> fetch origin <integration_branch> --quiet
# One record per commit: header line then a numstat block per commit — read from origin/<branch>
git -C <repo.path> log origin/<integration_branch> --no-merges --since=<since> --until=<until> \
  --numstat --date=iso-strict --format='__COMMIT__%H|%an|%ae|%cI|%s'
```

Map each commit to a PR-equivalent for the **same** tiering/bounty pipeline as Step 3+:
- **author** → match the commit author (`%an` / `%ae`) against `engineers.yaml` (its `github` login, or a `git_name`/`git_email` if present). Joy's commits are authored `JoyyCLangat`, which equals her `github` key.
- **changedFiles** → number of numstat rows for the commit (after the deductions in Step 3).
- **additions / deletions** → summed numstat columns (binary files show `-`; treat as 0 lines, still 1 file).
- **mergedAt** → committer date `%cI` (used for the time-window filter, same as PR `mergedAt`).
- **title / number** → subject `%s` (the trailing `(#NNNN)` is a **Fizzy card**, not a GitHub PR — label it as such in tables, don't link it as a PR).

Everything downstream is identical: deductions, LOWER-tier-wins classification, `inflate-suspect` flagging, bot/founder exclusion, and per-engineer `bounty_start_date` filtering all apply to git-log records exactly as to `gh-pr` records. There is no `gh pr view` enrichment for these repos (no reviews/commits API) — note that in the report where review-based signals would otherwise appear.

## Step 3: Classify PR Size Tiers

Each PR gets a tier based on scope signals:

| Tier | Files Changed | Lines (Add+Del) | Rate (KES) | Interpretation |
|------|--------------|-----------------|------------|----------------|
| **S** (Small) | 1–3 | < 300 | 500 | Bug fix, config tweak, copy change |
| **M** (Medium) | 4–10 | 300–800 | 1,000 | Feature slice, focused refactor |
| **L** (Large) | 11–25 | 800–2,500 | 2,000 | Full feature, multi-file refactor |
| **XL** (Extra Large) | 25+ | 2,500+ | 3,500 | Major feature, migration, restructure |

### Classification rule: LOWER tier wins

**Default:** A PR is classified by the **lower** tier when dimensions disagree. This prevents inflation from trivial multi-file touches or verbose code.

There is no critical-path override. Touching a complex file does not make a PR larger — the volume of actual work (files changed, lines written) does. What gets rewarded is output, not which part of the codebase was touched.

When dimensions disagree by 2+ tiers (e.g., files=L but lines=S), flag the PR as `inflate-suspect`.

Examples:
- 2 files + 200 lines → files=S, lines=M → **S** (default deflation)
- 15 files + 80 lines → files=L, lines=S → **S** + `inflate-suspect` flag
- 12 files + 800 lines → both L → **L**

### Deductions: what does NOT count

Before classification, subtract from the line count:
- **Generated/vendor files:** `package-lock.json`, `yarn.lock`, `deno.lock`, `*.generated.*`, `*.min.js`, `src/integrations/supabase/types.ts`, `public/sitemap.xml` (build-generated — see [.claude/rules/worktree-cleanup.md](../../../../.claude/rules/worktree-cleanup.md)'s disposable-dirt list, same category), any vendored library under a `vendor/` path
- **Lockfile-only PRs:** If the only changed file is a lockfile, classify as **noise** (not S)
- Migrations (`.sql` files) ARE counted — they represent real schema work
- **Always apply this deduction before tiering, not just when a PR "looks big."** September 2026 payout, Kennedy Kariuki's #2872 (a one-line ESLint rule enable): `gh pr view --json files` showed 4 files / 1,771 lines, and was priced M-tier (1,000 KES) off that raw total — but 1,761 of those 1,771 lines were a `package-lock.json` diff from an unrelated dependency bump riding in the same PR. Net-new content was 10 lines across 3 real files — S-tier (500 KES). Same root cause for Liban Hassan's #4009 (research SEO): a `public/sitemap.xml` build artifact contributed 52 of a 312-line total, pushing the PR from S-tier (260 lines) to M-tier (312 lines) — a single generated file crossing a tier boundary. **Fetch `--json files` and apply every deduction in this list for every PR you tier, not only the ones that already look abnormally large** — a generated file can flip a tier boundary even in an otherwise-small PR.

**Note:** The copy-paste deduction (>60% identical lines) is only applied when full diffs are available. If `gh pr diff` was not fetched for a PR, skip this check and note it in the report.

### Step 3a: Group by ticket, not by PR (mandatory — the real unit of payable work)

**A PR is not the unit of work. A Fizzy ticket is.** Before producing any bounty table, extract a ticket number from every remaining (non-promotion, non-revert) PR's title (pattern `#NNNN`) or branch name (pattern `NNNN/slug` / containing `NNNN`), and group PRs by that number. A single ticket routinely ships as a main PR plus 1-2 small follow-up fixes — that's normal delivery, not inflation, and the bounty table (Step 5f) must report and sum at the **ticket** level. A PR with no extractable ticket number stands alone as its own group.

**Why this is mandatory, not a nice-to-have:** a September 2026 manual audit (Tobi, 2026-10-01) found the skill's raw per-PR count was overpaying specifically because `split-suspect` (below) was defined loosely enough ("shared prefix or keywords") that a run-it-by-hand agent either under-applied it entirely (counted every PR) or over-applied it (collapsed PRs that were genuinely separate tickets shipped fast, just sharing a title prefix like `feat(analytics):`). Grouping by the actual ticket number first removes the ambiguity: PRs that share a ticket number are unambiguously one deliverable; PRs that merely share a title prefix but have *different* ticket numbers are unambiguously separate work and must never be collapsed into each other.

### Step 3b: Follow-up fixes are part of the ticket (mandatory)

Within a ticket group (Step 3a), pay the **highest-tier PR only**. Every other PR on that ticket pays **0**, unless that PR is itself M-tier or above. This applies regardless of who opened the follow-up: a fix on someone else's ticket is part of that ticket, not a separate payout. Show each as `follow-up: ticket #NNNN, PR #N → 0` in the report.

**Why this is mandatory:** September 2026. David Busuru flagged that his one-line fix (#405, +1/-1) on Liban Hassan's ticket #3681 had been paid 500 KES. An audit of the month found seven more follow-up PRs paid as separate S-tier lines (4,000 KES in total, from 2 to ~76 lines each) on tickets whose main PR was already paid. Paying S for every follow-up rewards splitting work into many PRs, not delivering more of it.

### Step 3c: Small-work floor (mandatory, effective October 2026 work)

After Step 3b collapses a ticket to its payable PR, if that PR has **fewer than 20 net lines** (after the generated-file deductions in Step 3) it pays **half rate**: an S-tier PR pays 250 KES, not 500. Lower-tier-wins means a PR under 20 lines is always S, so the floor only ever halves an S.

- **Applies to the ticket's payable PR** (the highest-tier one), not to every PR. A ticket whose best PR is under 20 lines pays 250.
- **List every floored PR in the report** as `floor: ticket #NNNN, PR #N, N net lines → 250`, with the engineer, so the manager can spot ones that matter.
- **Manager override:** during the 48-hour review (Step 7) the manager may mark a floored PR as *significant* (security patch, production-outage fix). It then pays full S. Log a one-line justification, same as other overrides.
- **Advances use the floored value.** An open-PR advance (Step 8) on a PR under 20 lines is 50% of the floored rate (125), and draw-down at merge re-applies the floor to the merged size.
- **Not retroactive.** Applies to work merged from 1 October 2026. The September 2026 payout is unchanged (Kennedy Kariuki's #2190 at 10 lines and #2191 at 14 lines were paid a full 500).

**Why:** September 2026. After the follow-up audit (Step 3b), the remaining case was tiny standalone tickets paid a full S (two of Kennedy's, 24 lines in total). The tier table has no minimum size, so these were legitimate under it; the floor is a policy decision by Tobi (2026-10-02), not a bug fix.

### Advisory flags

Most flags are **informational only** — the manager reviews during the 48-hour review period (Step 7). Exception: `split-suspect` is a **soft auto-deduction** (see below).

- **`split-suspect`**: within a single **ticket's** group of PRs (Step 3a) — not merely a shared title prefix — 3+ of them are **all S-tier** and merged within roughly a 24-hour window of each other. This is iterative fixup-commits-as-separate-PRs on the same piece of work, not 3 separate deliverables. **Soft auto-deduction:** collapse that S-tier sub-cluster into a single S payout (500 KES total instead of N × 500). Show in the report as `split-suspect: ticket #NNNN, merged [N] S-tier PRs → 1 × S`. A ticket's main feature PR, if M/L/XL, is priced separately and never folded into the collapse — only the S-tier fixup sub-cluster collapses. PRs on the same ticket more than ~24-48h apart are a legitimate later return to the ticket, not a split — do not force-collapse those. **Never collapse PRs that merely share a title prefix (e.g. `feat(analytics): ...`) but cite DIFFERENT ticket numbers** — that's parallel, separately-planned work shipped quickly, not one deliverable split up; treat each distinct ticket number as its own group per Step 3a. **Superseded in practice by Step 3b (v3.15.0):** a ticket now pays its highest-tier PR only, so an S-tier cluster never pays more than one S.
- **`inflate-suspect`**: Files/lines disagree by 2+ tiers (e.g., 20 files but 50 lines)
- **`churn-suspect`**: PR where deletions > 80% of additions AND net codebase change ≈ 0 (moved/renamed code). A PR that **net deletes** code (additions - deletions is significantly negative) is `cleanup` — not flagged, this is valuable work
- **`generated-heavy`**: >50% of lines are in files matching generated/vendor patterns
- **`revert-pair`**: PR title starts with "Revert" or body contains "reverts #NNN". Both the original PR and the revert are flagged. Net value = zero — exclude both from bounty
- **`duplicate-suspect`**: >80% of commits overlap with a previously closed (not merged) PR from the same author

## Step 4: Detect "Verify Deployment" / CI Noise

Count PRs with titles matching patterns like:
- `Verify deploy*`
- `Merge branch*` (auto-merge PRs)
- Exact duplicate titles from the same author within 5 minutes

Report these separately as **CI/deploy noise** so they don't inflate feature velocity.

### Step 4b: Promotion-PR exclusion (mandatory, structural — not title matching)

**Exclude any merged PR whose `headRefName` is itself one of the repo's configured `integration_branches`**, regardless of title, author, or repo. These are staging→main (or equivalent) promotion merges — the diff is a duplicate of feature PRs already paid when they landed on the earlier integration branch, not new authored work. Detect this with `gh pr view <n> --json headRefName` (or pull `headRefName` directly in the Step 2 `gh pr list --json` call — it's available there too, no extra API call needed) and compare against `repo.integration_branches`. Do **not** rely on title pattern-matching (`"Staging"`, `"Merge branch"`) as the primary signal — a promotion PR can be titled anything; the head-branch check is the only reliable one.

**Why this is mandatory, not advisory, and why it's called out separately from the title-based CI-noise check above:** this exact bug recurred for three consecutive monthly runs (July, August, September 2026) before being written into this file. July's payout found it, manually excluded it for that one report, and recorded "structural fix shipped to the pulse skill" in `reports/engineering-pulse/2026-07-verification.md` — but the fix was applied only to that report's numbers, never actually committed here. August's run had to re-derive and reapply the exact same exclusion from scratch (visible in `reports/engineering-pulse/2026-08-payout.md`'s "promotion PRs (head branch = integration branch) excluded structurally" note) — again without landing it here. September's run (this one) repeated the mistake a third time, overpaying one engineer by roughly 10,000 KES before a third manual catch. If you are an agent running this skill and you find yourself making this exclusion by hand again, that is the signal this section failed to prevent — fix the detection code path, don't just fix this month's table.

**Even the September "structural fix" itself initially under-applied this check — the exact bug recurred a 4th time, smaller, same session.** The v3.6.0 fix correctly checked `headRefName`, but the agent applying it that run still reached for the 3 PRs literally *titled* "Staging" and missed a 4th PR (nts #459) that had `headRefName == "staging"` but a normal-looking title (`"fix(#3961): remove S5 Your hosts section, renumber S6→05"`). A later manual ticket-level audit caught it. **The lesson: do not eyeball which PRs "look like" promotion merges and then verify just those. Programmatically check `headRefName` against `repo.integration_branches` for every single PR in the pulled set — the promotion PR with an innocuous title is the one this check exists to catch, not the one titled "Staging."** Before finalizing Step 5f's bounty table, do one explicit pass: for every PR in every author's row, assert `headRefName not in integration_branches`; if that assertion would fail for any PR still in the priced set, the table is wrong.

### Step 4c: Revert-pair exclusion (mechanical, not judgment)

A PR titled starting with `Revert "..."` (or whose body contains `reverts #NNN`) and the PR it reverts are both excluded — net value is zero, no judgment call needed. Match the reverted PR by the quoted title substring or the `#NNN` reference in the revert PR's own title/body.

### Step 4d: Stacked-branch duplicate-diff detection (for above-S-tier PRs, same author)

**This is a different bug than `split-suspect`.** `split-suspect` catches 3+ S-tier PRs on the *same* ticket; this catches two or more *different* tickets from the same author where the later PR's branch was cut from the earlier PR's branch instead of from the integration branch — so the later PR's reported diff re-includes the earlier ticket's files, inflating its tier.

**Detection:** for any author with 2+ M/L/XL-tier PRs merged within a few days of each other, fetch `gh pr view <n> --json files` for each and compare file paths across the pair. If a filename appears in both PRs with the **exact same (or near-identical) additions/deletions count**, that content was already paid for under the earlier PR — it is not new work in the later one.

**How to correct:** for each duplicated file, subtract its lines from the later PR's total and drop it from the later PR's file count (unless the line count differs meaningfully, in which case use only the delta as the incremental contribution). Re-tier the later PR on the resulting net-new files/lines. If the recomputed tier is lower, use the lower one — this is a real downward correction, not advisory.

**Why this exists:** September 2026 payout, Liban Hassan's resume-privacy epic (tickets A1→A2→A3, 3 separate Fizzy tickets) and activation-queue epic (tickets #3850→#3851). Each later PR's branch had been cut from the previous PR's branch rather than from `lovable-staging`, so GitHub's diff for A2 and A3 re-included A1's (and A1+A2's) files byte-for-byte — a single 803-line migration file was counted in all three PRs. Priced at face value, A2 and A3 both landed at L-tier (2,000 KES each); after removing the duplicated files, both drop to M-tier (1,000 KES each). #3851 "activation queue a11y" looked like M-tier (1,000 KES) but its only genuinely new content, after removing files byte-identical to #3850, was ~40 lines — S-tier (500 KES). Net correction: −2,500 KES on one engineer's month, caught only because the user's own skepticism ("I don't remember assigning him that much") prompted a file-level re-check — this detection should run by default, not only on manual challenge.

**Scope this check to pairs that are plausible candidates** (above S-tier, same author, merged within roughly the same week, especially PRs whose branch names look sequential — `A1/...`, `A2/...`, `3850/...`, `3851/...`) rather than diffing every PR against every other PR for every author — that's O(n²) `gh pr view` calls for no benefit on PRs that obviously don't share lineage.

**Run this check against EVERY repo the author touched that month, not just the repo where the first duplicate turned up.** The September 2026 run that discovered this bug initially found it only in one repo (`vettedai-audition-supabase-version`) and reported the fix as complete — a second, broader pass across the *same author's other repo that same month* (`nts-event-platform-supabase`) found an even larger instance: ticket #3683 "homepage programme states" was byte-for-byte identical across 11 files to the immediately-prior ticket #3682 (confirmed via `createdAt`: #3683's branch was opened before #3682 merged), reporting as L-tier (2,000 KES) when its genuine net-new content — two files the other ticket didn't touch — was S-tier (500 KES). A −1,500 KES correction that would have been missed entirely if the check had stopped after the first repo it was found in. One stacked-branch finding is a reason to broaden the search, not a reason to consider the author's other repos clean.

## Step 5: Generate the Report

Produce these sections as clean markdown tables:

### 5a. Per-Author Summary (excludes founder)
| Author | Login | PRs | Feature PRs | Files Changed | Lines (Add+Del) | Avg Lines/PR | Active Period |
Exclude CI noise from "Feature PRs". Show total in "PRs".

### 5b. Founder Activity (separate section)
| Login | PRs | Feature PRs | CI Noise | Files Changed | Lines (Add+Del) | PRs/Week |
Founder stats shown for context but NOT included in bounty calculations. Note: "Founder output is sweat equity. This section is for workload visibility, not bounty comparison."

### 5c. PR Size Distribution
| Author | S | M | L | XL | Flagged |
One row per author. Only count feature PRs (exclude CI noise). "Flagged" = count of PRs with advisory flags.

### 5d. Velocity
| Author | Feature PRs | Weeks in Window | PRs/Week |
Use the analysis window length (not first-to-last PR), so someone who shipped 4 PRs in a 4-week monthly window = 1.0/week even if all 4 were in week 1.

### 5e. Repo Breakdown
| Author | audition | congrats | backend | Multi-Repo |
Mark multi-repo contributors.

### 5f. Bounty Estimate
First, show the **ticket-level breakdown per author** (Step 3a groups): a table of Ticket # | description | PR count | tier(s) | payable KES. This is the evidence trail — it's what lets the manager (or a later audit) see *why* a number is what it is, not just the total. Then roll up:

| Author | S × 500 | M × 1,000 | L × 2,000 | XL × 3,500 | Gross (KES) | Revert Deductions | Net (KES) |

**Tier counts in this roll-up table are POST-ticket-grouping and POST-split-suspect-collapse** — i.e. they count payable ticket-level line items, not raw PRs. A ticket with 2 PRs (a feature + a follow-up fix) contributes 2 line items normally; a ticket with a collapsed S-tier cluster contributes 1.

**Gross** = sum of (tier count × tier rate) for all feature PRs.

**Automatic Deductions:**
- `revert-pair` — both the original and the revert are excluded (zero net value)
- `split-suspect` — collapsed to 1 × S payout. Show the saving: e.g., "split-suspect: 3 PRs → 1 × S (saved 1,000 KES)"

All other flags are advisory — the manager decides during review.

**Net** = Gross minus revert-pair deductions.

**Per-repo `bounty_multiplier` (check `repos.yaml` for every repo before finalizing any author's gross — mandatory, not optional).** Some repos carry an explicit `bounty_multiplier` in `repos.yaml` (currently: `manual-qa` and `vetted-automation`, both 0.5 — the "automation-mandate" rate, Tobi 2026-07, Addendum 4 in `reports/engineering-pulse/2026-07-payout.md`: a repo whose entire purpose is to automate QA that's *also* paid in full as manual-QA ops would double-pay for one outcome at full rate on both sides). Apply the multiplier to that repo's tier value **after** ticket-grouping/split-suspect collapse, and disclose it on the engineer's statement with the rationale — never a silent haircut.

**Why this is mandatory, not a one-time calculation:** this exact multiplier was correctly applied by hand in the July and August reports — it just never made it into `repos.yaml` as an actual setting, so it only existed as prose in two old report files. September's automated run missed it entirely, and a same-session manual re-verification of the same engineer's numbers *also* missed it, because nothing in the skill's own files said to apply it — it took the user's own memory of the July decision to catch the gap a third time. Any repo-specific rate adjustment must live in `repos.yaml` (or `engineers.yaml`) as a real field the skill reads, never only in a report's prose, or it silently stops being applied the moment nobody remembers to type it in by hand.

**Retainer / shadow-bounty split (Fix 3 + Fix 5).** Before totaling:
- For each `employment: retainer` engineer, the bounty + ops Net renders as `Shadow-bounty (not paid — retainer): X KES` with the footnote: _"Floor, not ceiling. Infra/security/investigation work is under-measured by line/task proxies — see the Capacity & Invisible Work section and value note."_ This is **internal-only** — never include it in an engineer-facing statement.
- `retainer_role: qa` engineers: **still surface their code output** as shadow-bounty in the Retainer ROI table (§5f-ter) — a QA person building automation tooling (Elvis in `vetted-automation`) is real output worth tracking (Tobi, 2026-07-01, superseding the earlier "suppress entirely"). But their shadow figure **understates a QA role** — always show it *alongside* their QA throughput (manual-QA sessions + tickets tested, §5g-bis), never as their standalone value.
- **Shadow-bounty retainer repos need the SAME re-derivation discipline as bounty repos, every run — "not paid" is not "not worth checking."** September 2026: Elvis's `vetted-automation` code output had been reported as 1 commit / 500 KES for at least four consecutive monthly reports, carried forward unchanged each time because it's unpaid and nobody re-ran the git-log pull. A direct re-check (fetch + full `git log --author` count) found **34 real commits that month** — the true figure, even after collapsing same-day same-topic clusters conservatively, was closer to 8,500 KES of code output alone. The ROI read against his retainer had been silently wrong for months. Re-run Step 2b's `git fetch` + full commit pull for every `source: git-log` repo on **every** run, shadow-bounty or bounty — a stale number that's merely "internal" still misinforms a real decision if anyone ever looks at it.
- **Team total payable EXCLUDES all shadow-bounty.** Compute "Team total payable" = sum of Net for `employment: bounty` engineers only. Show the shadow-bounty total separately as a clearly-labeled non-payable line, e.g. `Shadow-bounty (retained engineers, not paid): Y KES`.

### 5f-ter. Retainer Output — ROI signal (standard monthly section)

Render this table every run for **every** `employment: retainer` engineer. It's the durable monthly artefact for gauging retainer output against retainer cost — **not** a payout, and **never** shown to the engineer. Apply the same warranty/deliverable-collapse rules as bounty (so it's a conservative floor).

| Engineer | Role | Code output (KES) | Ops/QA (KES) | Shadow total | vs retainer cost |
|----------|------|------------------:|-------------:|-------------:|-----------------:|

- **Code output** = collapsed shadow-bounty from merged PRs / git-log commits (same tiering + collapse as bounty).
- **Ops/QA** = ops-category total (pr-review, manual-QA, etc.) from the Fizzy scan.
- **Shadow total** = Code + Ops/QA.
- **vs retainer cost** = `round(100 × shadow_total / retainer_kes_month)` (default 30,000). This is the ROI ratio.
- Sort by shadow total desc. Add the standing caveat verbatim: _"Floor, not ceiling — infra/security/QA work is under-read by line/task proxies. A low % (e.g. an infra/security engineer at 25%) is almost always under-measurement, not low output. Read alongside §5g-bis."_
- For `retainer_role: qa`, append a one-line callout with their QA throughput (manual-QA session count + tickets tested) so the % is never read as their value.

Show a **monthly projection** only for windows of 14+ days:
| Author | Net (KES) | Window Days | Projected Monthly (KES) | Projected Monthly (USD @ 130) |
For windows under 14 days, show actuals only with a note: "Window too short for reliable monthly projection."

### 5g. Reviews Given
| Author | Reviews Given | Substantive Reviews (with comments) | Avg Review Turnaround (hours) |
Pull from `gh api` review data. This section is informational — review work is not bounty-compensated in v2 but is surfaced so the manager can factor it into payout decisions.

### 5g-bis. Capacity & Invisible Work (signal, not payment)

This section captures the work that line/task proxies systematically under-read — infra, security, investigation, review, QA — as **robust structural counts**, never keyword-based paid categories. Show it next to shadow-bounty so a low shadow figure is immediately contextualized (a low number for an infra/security engineer is almost always under-measurement, not low output — strategy §2). One row per engineer:

| Engineer | PRs Reviewed | Tickets Resolved-by-Comment | QA Verdicts (tickets tested) | Open / In-Flight PRs | Open PR Lines (Add+Del) |

Computation:
1. **PRs reviewed** — count of **distinct cards** where the engineer authored a matched `pr-review` comment. Already detected; just surface the deduped-per-card count (Fix 5 dedup). Cheap.
2. **Tickets resolved-by-comment** — count of cards the engineer closed or where their comment drove closure. Detection: their authored comment matches `closing as|closed as|resolved —|superseded by|obsolete|no action needed|stale` near the start, OR they are the actor on the card's closure event. This is a **count, not a paid category** — it captures investigation/triage (Theo's largest contribution type) without parsing prose.
3. **QA verdicts (tickets tested)** — from the `qa-verdict` surface (structural column-move into/out of a QA column + format-tolerant regex). Distinct cards. For qa-role retainers this is the primary capacity measure. (May reality: Elvis ≈ 227 verdicts across 190 distinct cards — the old `manual-qa` keywords saw 7.)
4. **Open / in-flight PRs (+ lines)** — `gh pr list --state open --author <login>` per repo, summing additions+deletions. Surfaces work trapped in review/CI (Kenn's ~9k unmerged lines would show here). **Counts and lines only — do not tier or pay.**

These four are **explicitly signal, not payment.** Do NOT convert them into bounty subtotals. They contextualize shadow-bounty and inform the conversion / capacity decision (strategy §4, §6). For any engineer or surface not actually scanned (missing `fizzy_user_id`, repo outside the allowlist), print **"not measured"** in the cell — never an implied 0 (strategy coverage rule: a silent zero reads as "did nothing"; it usually means "we didn't look there").

### 5h. Summary Table
| Author | Feature PRs | Dominant Tier | PRs/Week | Top Repo | Net Bounty (KES) | Flags |
Flags to include:
- `< 1 PR/month` — less than 1 feature PR per month (averaged over window)
- `multi-repo` — contributes to 2+ repos
- `XL-heavy` — more than 50% of PRs are XL tier
- `noise-heavy` — more than 30% of PRs are CI/deploy noise
- Advisory flags from Step 3 (split-suspect, inflate-suspect, etc.)

### 5i. Management Insights

After the tables, add a **Management Insights** section with actionable observations:

1. **Workload balance** — Is one person carrying the team? Are others underutilized?
2. **Delegation opportunities** — Based on repo breakdown, who could take on more in an underserved repo?
3. **PR hygiene** — Anyone consistently shipping XL PRs that should be broken down? Anyone with a high noise ratio?
4. **Growth signals** — Is anyone's velocity increasing or decreasing compared to prior periods? (Only if prior data available)
5. **Risk flags** — Single points of failure (one person owns an entire repo), idle contributors, or bus factor concerns.
6. **Bounty ROI** — For each contributor, is the estimated payout proportional to the value delivered? Flag anyone where the bounty seems disproportionate to output quality.
7. **Blind spots** — This report measures merged code output only. Investigation, debugging, architecture review, incident response, code review, and mentoring are NOT captured. The manager should adjust payouts for contributors whose primary value is diagnostic or architectural.
8. **Conversion watch (auto-flag).** Auto-flag any **bounty** engineer (`employment: bounty`) whose trailing figure (bounty + ops Net, ideally over 2–3 months) ≥ ~70% of a reference retainer (default 30k, i.e. ≥ ~21k) as a **conversion candidate**. Surface the §4 three-gate checklist for the manager: (1) shadow-bounty ≥ ~70–80% of retainer cost over a trailing 2–3 months, (2) capacity headroom looks real (velocity, multi-repo spread, responsiveness), (3) quality is clean (low revert rate, low QA-fail rate, few flags). Below the bar, keep them on bounty — it's cheaper, flexible, self-limiting. (May: Daniella ≈ 29.6k clears the gate today; next is DBusuru ~16k, not close.)
9. **Per-retained-engineer value note.** For each `employment: retainer` engineer, render a templated 1–2 line free-text field (`value_note`, filled monthly by the manager) — e.g. _"Oussama — webhook hardening + memory-exhaustion fix; high-leverage security, low line-count by nature."_ This is the only judgement of an infra/security engineer's value that should carry weight; the shadow-bounty is a floor, never a ceiling (strategy §2, §5). Leave a blank placeholder line if the manager hasn't supplied one this period.
10. **Coverage / "not measured" honesty.** Explicitly list every surface or person we did NOT scan this run (missing `fizzy_user_id`, repos outside the allowlist, dormant boards). Print "not measured" for each — never let an un-scanned person read as a zero. When a number looks shockingly low, suspect coverage before performance.

## Step 6: Save the Report

Reports are saved based on their type — **draft** (mid-month check-ins) or **payout** (end-of-month final).

### Report types

| Type | When | File name | Purpose |
|------|------|-----------|---------|
| **Draft** | Any weekly/ad-hoc run during the month | `reports/engineering-pulse/YYYY-MM-DD-draft.md` | Velocity check, early flags, no payout implications |
| **Payout** | End of calendar month (run on the 28th) | `reports/engineering-pulse/YYYY-MM-payout.md` | The official bounty report for that month's cycle |

**Auto-detect:** If the user runs `/engineering-pulse monthly` and today is the 28th–31st of the month, default to **payout** type. Otherwise default to **draft**. The user can override with `--payout` or `--draft` flags.

### Draft reports

```
reports/engineering-pulse/YYYY-MM-DD-draft.md
```
Frontmatter includes `type: draft`. The bounty table header reads: "**DRAFT — not for payout.** Mid-month check-in only."

Draft reports do NOT trigger the review period. They're for the manager's eyes to course-correct (e.g., "Kariuki11 has zero PRs this month — check if he's blocked").

### Payout reports

```
reports/engineering-pulse/YYYY-MM-payout.md
```
Frontmatter includes `type: payout`. This is the single source of truth for that month's bounties.

**Window:** Always 1st of the month → last day of the month (calendar month). The `--since`/`--until` are auto-set:
- `--since` = first day of current month (e.g., `2026-03-01`)
- `--until` = today (or last day of month if running on the 28th+)

**Cumulative:** If draft reports were generated during the month, the payout report supersedes all of them. There is no "roll-up" — the payout report recalculates everything from scratch for the full calendar month.

Create the directory if it doesn't exist. Include a YAML frontmatter header:
```yaml
---
report: engineering-pulse
type: payout
generated: 2026-03-28
window: 2026-03-01 to 2026-03-28
repos: [audition, congrats, backend]
total_prs: 142
contributors: 6
bounty_rates_kes: { S: 500, M: 1000, L: 2000, XL: 3500 }
classification: deflation-bias
review_period_ends: 2026-03-30
payout_date: 2026-03-31
---
```

## Step 7: Monthly Payout Cycle

Payouts happen at the end of each calendar month. The timeline:

```
28th  → Generate payout report (run /engineering-pulse monthly --payout)
28th  → Share bounty table with contributors
30th  → 48-hour dispute window closes
31st  → Manager confirms final amounts, payout processed
```

If the month has fewer than 31 days, shift accordingly (e.g., Feb: 26th → 28th).

### During the 48-hour review period:

1. **Share bounty table with contributors** — each person sees their own row plus the flag explanations
2. **Dispute window** — contributors can provide context for any flagged PR (e.g., "this churn-suspect was the migration cleanup you assigned me")
3. **Manager resolves disputes** — one-line justification logged in the report for each override
4. **Final payout** — after the review period closes, the manager confirms the net amounts

### Rule-change note for the monthly DM

The monthly DMs (`notify.py` in the vetted-invoices repo) carry a one-line **"what changed this month"** whenever a payout rule changed since the last announcement. Each run: draft that line from the changelog below for every entry marked `announced: no`, show it to the manager, and mark it `announced: yes` only after the manager confirms the DMs went out. Never send it automatically.

Rule changelog:
- 2026-10 — Follow-up fixes (v3.15.0): a ticket pays its highest-tier PR only; extra PRs on it pay 0 unless M+. Already applied to the September payout. `announced: no` (only David was affected and was told directly)
- 2026-10 — Small-work floor (v3.16.0): a standalone PR under 20 net lines pays half rate; applies to October 2026 work onward. `announced: no`
- 2026-10 — Stale-PR review (v3.16.0): PRs open 60+ days are flagged for manager review each month; nothing expires automatically. `announced: no`

### Late PRs (merged after the 28th)

PRs merged between the 28th and end of month are included in the **next** month's payout report. The cutoff is the `--until` date in the payout report. This avoids re-generating the report after disputes are resolved.

### Mid-month draft cadence (recommended)

Run a draft report weekly or bi-weekly to catch issues early:
- **Week 2 draft:** Are contributors on track? Anyone with zero PRs who might be blocked?
- **Week 3 draft:** Flag any gaming patterns early so the end-of-month payout report is clean

Drafts use the same classification logic but are labeled clearly as non-binding.

This step is process, not code — the payout report should include the `review_period_ends` and `payout_date` in the frontmatter and a note at the bottom: "Bounty estimates are preliminary until the review period closes on {review_period_ends}. Final payout on {payout_date}."

## Step 8: Pre-Invoice Mode (`--pre-invoice`)

When the user passes `--pre-invoice` (or asks for "pre-invoices" / "bounty statements"), generate one engineer-facing markdown statement per active engineer in addition to the team payout report. These statements are what the engineer uses to issue an invoice; they must be self-contained, accurate, and free of internal-only signals (no flags, no comparisons to other contributors, no management insights).

### Inputs

1. **`engineers.yaml`** (next to this SKILL.md) — registry of active engineers with display name, reference initials, and currency. Engineers absent from this file are still counted in the team payout report but no statement is generated for them.
2. **`reports/payouts/balances.json`** (in the working repo) — append-only ledger of explicit advance agreements. Most months it's empty. Each entry has lifecycle: `pending` → `applied` (one or more periods) → `settled`. Each pending entry can include an `apply_when` condition (currently supports `gross >= NNNN`, `gross > NNNN`, etc.) that gates auto-application — useful when an advance shouldn't be drawn down until the engineer's monthly gross bounty crosses a threshold (so we don't compound assignment shortfalls). When the condition is met, the skill proposes applying the advance; when it isn't met, the engineer's statement renders a "carried forward" block explaining the rollover. The skill never auto-writes entries — manual confirmation required (see the confirmation gate below) — but it MUST always **propose** the two things below; silently skipping the proposal is the actual failure mode this note exists to prevent (it happened: this step existed only as a section header in old report prose, "Open-PR half-bounty (policy, effective July 2026)," with no SKILL.md procedure behind it — several months' worth of still-open PRs went unvalued as a result, discovered only when an unrelated audit went looking for it).
   - **Open-PR half-bounty (policy, effective July 2026): every run must check for NEW advances to propose, not just apply existing ones.** For every bounty engineer, list PRs opened in the period but still unmerged at the period's end (`gh pr list --state open --author <login> --created <period-range>`). Value each at its tier (same files/lines rules as merged PRs) and propose a new `pending` entry at 50% of that total, with `pr_list` naming every PR and `valued_at_open_kes` the full-tier sum — mirror the existing entries' schema exactly. Surface this as an explicit confirmation prompt alongside any existing-advance draw-downs; never silently omit it because "nothing changed" — a new advance is itself a kind of change.
   - **Draw-down is per-PR, not per-entry.** When a listed PR later merges, re-tier it at merge time and pay only the REMAINING 50% (full tier value minus what was already advanced) — never re-pay the first half. A PR that closes unmerged forfeits its unpaid half; no clawback of the half already paid.
   - **Stale-PR review (60 days, effective October 2026 run):** every run lists each PR in a `pending` advance entry that has been open **60+ days, counted from the PR's open date** (not the advance date), with its engineer, age and pending half. Surface it as a table for the manager to decide each one (keep waiting / ask the engineer / close and forfeit). **Nothing expires automatically** — a stuck PR may be waiting on review, not the engineer. Known at 2026-10-02, to appear in the October run: Kennedy Kariuki #337, #338, #343, #375, #1763 (65–81 days, 4,250 KES pending) and oussama22x #314, #318, #334 (82–89 days, 1,000 KES pending).
3. **`pre-invoice-template.md`** (next to this SKILL.md) — markdown template with placeholders for the rendering step.

### Output

One statement per active engineer at `reports/payouts/<period>/<period>_<github_login>.md`. The period subfolder groups all statements for a given month or half-month together.

- Monthly payout runs: period = `YYYY-MM` → `reports/payouts/2026-04/2026-04_DBusuru.md`
- Half-month runs: period = `YYYY-MM-DD-to-DD` → `reports/payouts/2026-03-16-to-30/2026-03-16-to-30_DBusuru.md`

Create the subfolder if it doesn't exist. Filename uses the github login (deterministic, unambiguous) — not the display name.

### Rendering rules

- **Work table:** one row per feature PR (exclude CI noise and revert-pairs). Columns: ticket label (extract from PR title — e.g., "[#414] …" or "ticket 5.3"), repo name, PR number, tier, amount. PRs flagged as `duplicate-suspect` or as setup-noise (e.g. titles like "Author ( the branch)") have their amounts struck through (`~~500~~`) and footnoted; they are NOT included in the gross.
- **Tier summary:** one row per tier present, with PR count, rate, subtotal. Counts only the kept (non-struck) PRs.
- **Gross bounty:** sum of subtotals.
- **Advance block:** present only if `balances.json` has an advance entry for this engineer that is either (a) `pending` with an `apply_when` condition the current gross satisfies → render an "Applied This Month" block, OR (b) `pending` with the condition not yet satisfied → render a "Carried Forward" block, OR (c) `settled` with `applied_period == current period` → render a historical "Applied This Month" block. If no entry matches, omit the block entirely. Use the friendly month name in headings ("March Advance — Carried Forward", not "2026-03 Advance — Carried Forward").
- **Volume note:** present only when the manager has supplied a per-engineer note for the period. Don't auto-generate volume notes from velocity data — the manager decides when context is owed.
- **Footnotes:** if any rows are struck through, append a `## Notes for Review` section explaining each. Tone: factual, second-person, invite the engineer to flag if our judgment is wrong.
- **Net total:** `gross - applied_advance`. This is the amount the engineer invoices.
- **Reference code:** `GC-ENG-<period>-<reference_initials>`. For half-month periods append `A` or `B` (`GC-ENG-2026-03B-DB`).

### Tone

These statements are sent to the engineer. Write everything in **plain second-person prose** as if you're the manager talking to the contractor:

- ✅ "In March we paid you KES 5,000 against work that came in at KES 2,500..."
- ❌ "March overpayment from bounty rubric calibration. Originally agreed to draw down against April work..."

Avoid third-person references to the engineer ("David's gross", "Daniella's PRs"), accounting jargon ("recover", "reconciliation entry"), and judgmental language ("penalize"). When the cause of a discrepancy is on the platform side (light assignment, rubric calibration), name it explicitly and take responsibility — engineers notice when statements quietly skip the why.

The `rationale` field in `balances.json` is rendered verbatim into the engineer-facing block, so it must already be in this voice. Do not write internal-finance language there.

### Confirmation gate before writing balances.json

After rendering the statements but **before** writing the updated `balances.json`:

1. Print a diff summary to the console: which advances would transition `pending` → `applied` or `applied` → `settled`, with engineer names and amounts.
2. Wait for explicit user confirmation (`y` / `yes`).
3. Only on confirmation, write the updated `balances.json`.

This kills the double-count risk if the skill is re-run for the same period — running again without confirmation produces the same statement files but the ledger is unchanged. Idempotency is keyed on `(advance.id, applied_period)`.

### Ops & Review Contribution Detection

In addition to bounty (merged PRs), engineers earn for skill-assisted ops work that lives in Fizzy comments — pr-review runs, qa-handoff guides, ticket-review panel runs, and manual QA sessions. These are real contributions that don't show up in `gh pr list`.

**Inputs:**
1. **`ops-rates.yaml`** (next to this SKILL.md) — defines categories, rates (KES), keyword detectors, minimum comment length, and the list of Fizzy boards + card-number range to scan.
2. **`fizzy_user_id`** field on each engineer in `engineers.yaml` — required for attribution. Discoverable from any card's `/comments.json` endpoint by inspecting `creator.id`.

**Algorithm:**
1. For each card number in `ops-rates.yaml > card_scan_range`, fetch `/comments.json` (parallelize via thread pool, ~25 workers, ~10 seconds for 800 cards). Also fetch the card metadata itself (`/cards/{n}.json`) so card creators can be matched for the prod-triage category.

   **The comments endpoint paginates at 15 comments/page** via a `Link: <…?page=2>; rel="next"` response header. You MUST follow the `Link` rel="next" header to exhaustion per card, or you silently drop every comment past the 15th on busy cards — exactly the high-traffic infra/QA threads you most want to see (e.g. May card #179 had 47 comments; reading page 1 only saw 15). This under-counts everyone. The `get()` helper must return both the parsed body AND `resp.headers.get('Link')`. Reference implementation (verified working 2026-05-30):

   ```python
   def scan(n):
       out = []; url = f'https://app.fizzy.do/{ACCT}/cards/{n}/comments.json'; pages = 0
       while url and pages < 12:                      # 12-page safety cap
           data, link = get(url)                      # get() must also return resp.headers.get('Link')
           if not isinstance(data, list): break
           out.extend(data); pages += 1
           m = re.search(r'<([^>]+)>;\s*rel="next"', link or '')
           url = m.group(1) if m else None
       return n, out
   ```
2. Filter to: authored by an active engineer (via `fizzy_user_id` map) within the analysis window AND on/after the engineer's `bounty_start_date` if set. (See "Per-engineer bounty start date" below.)
3. Classify each surface independently:
   - **Comment-based categories** (`ticket-review`, `pr-review`, `qa-handoff`, `manual-qa`): walk in priority order. A comment matches if it (a) meets `min_length`, (b) hits any of `detect_any` keywords, AND (c) hits all of `detect_all` clauses (each clause requires any of its keywords). Unmatched comments longer than `track_other_min_length` surface as "uncategorized" so the manager can refine the detectors.
   - **Card-creation categories** (`prod-triage`): when a category specifies `surface: card_creation`, scan card metadata instead of comments. Match if the card was created by the engineer's `fizzy_user_id`, on a board in the category's `boards` list, with a title hitting any of `title_detect_any`. Each matching card counts once at `rate_kes` regardless of how the engineer later updates it.
   - **QA-verdict surface** (`qa-verdict`, `surface: qa_verdict`): a CAPACITY count (tickets tested), NOT a paid category. Detect a QA verdict by the **structural** signal first — a card moved into or out of any column in `qa_column_ids` is a QA action regardless of comment wording — then by the **format-tolerant** `verdict_regex` (case-insensitive) for comment-only sign-offs/blocks. Do NOT rely on the narrow `manual-qa` keywords for qa-role engineers: they miss ~97% of real QA verdicts (`TICKET #X — QA REVIEW SIGN-OFF` / `QA BLOCK` / `UI TESTING SIGN-OFF`). Dedup per distinct card; optionally split block/fail vs sign-off/pass via `block_regex` / `signoff_regex`. Surfaces in "Capacity & Invisible Work", not in the ops payable total.
4. **Dedup ops matches per `(engineer, card, category)` — we do not pay for re-reviewing/re-testing the same card** (Tobi, 2026-05-30). Within a single card, collapse repeat matches of the same category by the same engineer to ONE. **Distinct-sub-branch exception:** a single Fizzy card carrying multiple distinct sub-branch PRs (e.g. #672 = 672a–e) counts each distinct branch — detect distinct branch/PR refs in the matched comments and credit one per distinct ref; fall back to per-card (one) if no distinct refs are found.
4b. **Self-QA / self-review does NOT double-pay** (Tobi, 2026-07-01). An ops match (manual-QA, pr-review, ticket-review, qa-handoff) on a Fizzy card the **same engineer also authored code for in the window** is part of shipping that ticket — already covered by the code bounty + warranty — and is **excluded from paid ops**. Build `authored_tickets[engineer]` = the set of card numbers each engineer wrote code for (extract `#NNNN` / `(NNNN)` refs from their PR titles + git-log commit subjects, all records incl. excluded). When an ops comment by engineer E lands on card N, credit it only if `N ∉ authored_tickets[E]`. QA/review of **another** engineer's ticket still pays in full — this is why a dedicated QA role (Elvis) is credited for the bulk of their throughput while a code engineer QA-ing their own feature is not. Report the excluded self-QA total per engineer for transparency (don't silently drop it). NOTE: this is a **paid-ops** rule only — the `qa-verdict` capacity surface (§5g-bis) still counts self-verdicts, since capacity is a throughput signal, not a payout.
5. Sum per-engineer per-category: `count × rate_kes` = subtotal. Net ops = sum of all category subtotals.

   **Retainer awareness (see `engineers.yaml > employment`):**
   - `employment: bounty` (or absent) → ops + bounty figure is **payable**; behaves as today.
   - `employment: retainer`, `retainer_role: engineering` → compute bounty + ops as **shadow-bounty (not paid — retainer)** (Fix 5). EXCLUDE it from team total payable; show it separately, labeled.
   - `employment: retainer`, `retainer_role: qa` → **suppress the PR/shadow-bounty entirely.** Measure on QA throughput (manual-QA sessions + tickets tested via the `qa-verdict` surface) in "Capacity & Invisible Work". Near-zero QA throughput in the window is a flag to surface, not a number to compute.

**Per-engineer bounty start date.** When an engineer's `bounty_start_date` is set in `engineers.yaml`, all PRs / comments / card creations attributed to them must satisfy `event_date >= bounty_start_date`. Pre-agreement work is not bounty-eligible — even if it shipped during the analysis window. Apply the filter at the source-merging step (PR `mergedAt`, comment `created_at`, card `created_at`), not as a downstream filter, so subtotals are accurate from the start. If the field is missing or null, no filter is applied.

**Rate effective dates.** When `rate_effective_from` is set on a category, the rate applies only to events on or after that date. For events before the effective date, fall back to the previous rate (recorded in the category comment). The skill should never silently re-rate historical periods; if the manager runs `--pre-invoice` for an old period after a rate change, the older rate should still produce the original numbers.

**Render in statement:**
- New section "Ops & Review Contributions" (after "Bounty Summary") with one row per category present.
- Net payable becomes `bounty_gross + ops_total - applied_advance`.
- If the engineer has bounty AND ops, the statement also includes a "Total" block summing the two before the advance/invoice section so the engineer can read the math at a glance.

**Tone in the section:** "These are skill-assisted reviews, QA testing guides, and manual QA sessions you posted to Fizzy this month — work that doesn't show up as merged PRs." Acknowledges the contribution without overselling it (the AI did most of the heavy lifting; we're paying for the human in the loop).

**Calibration philosophy:** rates are deliberately low because most of these tasks are AI-assisted — the engineer's value is invoking the skill, sanity-checking, and adding context. Manual QA is the exception (real testing-the-app time) and gets a higher rate. If a category becomes high-volume for a single engineer (say 30+ runs/month consistently), that's a signal to formalize the role (flat retainer for QA, etc.) rather than scaling the per-task rate up.

**False positives & manager review:** the detectors are heuristic and produce some misclassification. Daniella's April scan, for example, flagged 16 "uncategorized" long comments (file-summaries written for context that aren't a defined category). The team payout report surfaces these so the manager can decide whether to add a new category, manually credit, or ignore. The skill never silently inflates — what it shows is what was matched.

### Founder, QA, and unregistered contributors

- **Founder:** never gets a pre-invoice statement (sweat equity).
- **QA (Elvis):** never gets a PR-based statement. As a `retainer_role: qa` engineer he is measured on QA throughput (manual-QA + `qa-verdict` tickets tested) in Capacity & Invisible Work, not on PRs or shadow-bounty.
- **Retainer engineers (`employment: retainer`):** never get a payable pre-invoice statement — the retainer does not stack with bounty. Their bounty + ops is computed as internal-only **shadow-bounty** (a floor, not a ceiling) and excluded from team total payable. The only thing ever shared with a retained engineer is the value note, never the shadow-bounty number.
- **Engineers with PRs but no `engineers.yaml` entry:** team payout report counts their bounty; no statement file is written. The skill prints a one-line warning suggesting the user add them to `engineers.yaml` if they should be invoiced.

### Machine-readable payout export (`--payout-json`)

When the user passes `--payout-json` (in addition to `--pre-invoice`), also emit a single machine-readable file at `reports/payouts/<period>/payout.json` — the same numbers as the markdown statements, in a form a downstream tool can consume without parsing prose. This is what feeds the `vetted-invoices` static site (its local `publish.py` reads this file and writes the per-engineer invoice pages).

**Keep this file consumer-agnostic.** It is keyed by GitHub login and knows nothing about invoice tokens, Netlify, or any specific site — that coupling lives entirely in the consumer. Do not add token/URL fields here.

Shape: a JSON array, one object per engineer who got a statement (retainer engineers included — they invoice their flat retainer even though they get no *bounty* statement). Fields:

```json
[
  {
    "github": "daniella-mu",              // engineers.yaml primary key (join key downstream)
    "display_name": "Daniella Mutai",
    "employment": "bounty",               // "bounty" | "retainer"
    "reference_code": "GC-ENG-2026-06-DM",// GC-ENG-… for bounty, GC-RET-… for retainer
    "period_label": "June 2026 (1–30 June)",
    "generated": "2026-06",               // the period key
    "code_total": 30000,                  // bounty gross (net of struck rows)
    "ops_total": 5385,
    "net_total": 35385,                   // code_total + ops_total − applied_advance; the amount invoiced
    "work":  [ {"title": "...", "repo": "nts", "tier": "L", "amt": 2000} ],
    "tiers": [ {"tier": "S", "count": 40, "rate": 500, "subtotal": 20000} ],
    "ops":   [ {"label": "PR Review (skill-assisted)", "count": 39, "rate": 40, "subtotal": 1560} ]
  },
  {
    "github": "jush34",
    "display_name": "Theophilus Juma",
    "employment": "retainer",
    "reference_code": "GC-RET-2026-06-TJ",
    "period_label": "June 2026 (1–30 June)",
    "generated": "2026-06",
    "retainer_kes_month": 30000           // retainer people carry this instead of the bounty fields
  }
]
```

Rules that keep it faithful to the statements:
- `net_total` already reflects any applied advance (same figure the engineer is told to invoice). `work`/`tiers` exclude struck (duplicate-suspect / setup-noise) rows, matching the statement.
- Retainer engineers: emit `employment: "retainer"` + `retainer_kes_month`, and use the `GC-RET-…` reference code. Do **not** emit their shadow-bounty numbers here — the flat retainer is what they invoice.
- Amounts are integers (KES). No currency symbols, no thousands separators.

## Bounty Rate Reference

These rates are fixed in KES (Kenyan Shillings). They are intentionally conservative — the team is bootstrapped and operating in the East African market.

| Tier | Rate (KES) | ~USD @ 130 | Scope |
|------|-----------|------------|-------|
| S | 500 | ~USD 3.85 | Single, well-defined output with a clear finish line (bug fix, copy edit, UI tweak) |
| M | 1,000 | ~USD 7.70 | Complete deliverable with multiple steps or components (new feature, process doc) |
| L | 2,000 | ~USD 15.40 | Substantial end-to-end deliverable spanning multiple sessions (full feature, campaign, detailed report) |
| XL | 3,500 | ~USD 26.90 | High-judgment deliverable requiring significant planning, iteration, or cross-functional context (system architecture, go-to-market strategy, full product spec) |

### Role-specific notes

- **QA (Elvis/Much1r1):** QA work is measured by defect escape rate and test coverage, not PR volume. Elvis is excluded from the PR-based bounty table and tracked separately. If QA contributors submit code PRs, those are bounty-eligible like anyone else's.
- **New contributors (first 30 days):** Contributors in their first 30 days of activity are marked with a `ramping-up` tag. Their tier distribution is shown for context but the manager should expect S-heavy output during onboarding — this is normal, not underperformance.
- **Founder:** Tracked in a separate section for workload visibility. Not bounty-eligible (sweat equity).

## Implementation Notes

- Run all `gh pr list` commands in parallel (one per repo) for speed; for `source: git-log` repos substitute the `git log --numstat` pull from Step 2b (also parallelizable)
- Fetch `gh pr view` data (files, reviews) only for PRs above S-tier threshold to avoid API rate limits
- Use Python for data processing — it handles JSON, dates, and table formatting well
- The analysis script is self-contained in a Python block. **Allowed deps: stdlib + `pyyaml`** (for parsing `repos.yaml`, `engineers.yaml`, `ops-rates.yaml`). Install with `pip3 install --quiet pyyaml` if missing.
- **Fizzy auth:** the `--pre-invoice` mode hits the Fizzy API for ops detection. Source the token from `.env.local` before running: `set -a && source <repo>/.env.local && set +a` — exposes `FIZZY_API_TOKEN` for the Python script to read via `os.environ`. See [.claude/rules/env-local-credentials.md](../../../../.claude/rules/env-local-credentials.md).
- **Fizzy API patterns:** use `urllib.request` (stdlib) with `Authorization: Bearer ${FIZZY_API_TOKEN}` and `User-Agent: VettedAI/1.0`. Always append `.json` to action endpoints. See [.claude/rules/fizzy-api-patterns.md](../../../../.claude/rules/fizzy-api-patterns.md). Parallelize card-fetches via `ThreadPoolExecutor(max_workers=25)` — ~10 seconds for 800-card scan.
- **Fizzy comments paginate at 15/page via `Link: rel=next` — follow to exhaustion or you silently undercount busy cards.** The `get()` helper must surface `resp.headers.get('Link')` so the scan loop can chase `rel="next"` (reference loop in the Ops algorithm, step 1).
- **Fizzy comment `body` is an object `{plain_text, html}`, NOT a bare string.** Read `body['plain_text']` (fall back to stripping `body['html']`); treating `body` as a string throws `TypeError`. Same for QA-verdict / resolved-by-comment detection.
- **Card scan range** in `ops-rates.yaml > card_scan_range` should be tuned periodically as Fizzy card numbers grow. Underestimating misses recent ops; overestimating just costs a few extra seconds.
- If lines/files counts look anomalous (e.g., >50K lines in a single PR), flag it as likely containing generated/vendor files
- Always note the CI noise percentage in the final summary so managers see the true signal
- **Deflation bias:** default to lower tier. The goal is accuracy, not punishment
- **Flags are advisory only:** show them prominently so the manager can decide during the review period. Never silently downgrade — transparency builds trust
- **Revert-pairs are the one automatic deduction** — merged-then-reverted PRs have zero net value, no judgment needed
- When showing bounty estimates, show gross and the revert deduction so the delta is clear

## Bounty + Ops Reference

| System | Source of truth | What it counts |
|---|---|---|
| Bounty (PRs) | `gh pr list` across `repos.yaml` (or `git log --numstat` for `source: git-log` repos) | Merged PRs / direct-push commits into integration branches, tiered S/M/L/XL by lower of files/lines |
| Ops contributions | Fizzy comments + card creations across `ops-rates.yaml > boards` | pr-review, qa-handoff, ticket-review, manual-qa (comments) + prod-triage (card creations). Deduped per `(engineer, card, category)` — no re-reviews; distinct-sub-branch exception |
| Capacity & Invisible Work (signal, not paid) | Fizzy comments + `gh pr list --state open` | PRs reviewed, tickets resolved-by-comment, QA verdicts (tickets tested), open/in-flight PRs + lines |
| Employment / payability | `engineers.yaml` `employment` | `bounty` → payable; `retainer` → shadow-bounty (not paid, excluded from team total); `retainer_role: qa` → suppress shadow-bounty, measure on QA throughput |
| Advances | `reports/payouts/balances.json` | Explicit advance agreements, lifecycle pending → applied → settled |
| Per-engineer eligibility | `engineers.yaml` `bounty_start_date` | Filter applied to PRs / comments / card creations: `event_date >= bounty_start_date` |
