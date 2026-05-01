---
name: engineering-pulse
description: Cross-repo engineering productivity analysis with bounty estimation. Use when the user wants contributor stats, PR velocity, workload distribution, team performance snapshots, or bounty payout projections.
version: 3.0.0
license: MIT
metadata:
  author: VettedAI
  category: engineering-management
  tags: [productivity, performance-review, team-health, velocity, delegation, bounty]
  created: 2026-03-11
  updated: 2026-05-01
argument-hint: "[weekly|monthly|quarterly] [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--pre-invoice] [--draft|--payout]"
---

# Engineering Pulse — Contributor Productivity & Bounty Analysis

Generates a cross-repo contributor analysis from merged PR data with bounty payout estimates. Designed for weekly standups, monthly reviews, quarterly performance cycles, delegation planning, and bounty reconciliation.

> **Philosophy:** Deflation bias. This is an AI-assisted workflow — agents write most of the code, engineers supervise and validate. We pay for judgment and output, not volume. When in doubt, the lower tier wins.

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
- **Generated/vendor files:** `package-lock.json`, `yarn.lock`, `deno.lock`, `*.generated.*`, `*.min.js`, `src/integrations/supabase/types.ts`
- **Lockfile-only PRs:** If the only changed file is a lockfile, classify as **noise** (not S)
- Migrations (`.sql` files) ARE counted — they represent real schema work

**Note:** The copy-paste deduction (>60% identical lines) is only applied when full diffs are available. If `gh pr diff` was not fetched for a PR, skip this check and note it in the report.

### Advisory flags

Most flags are **informational only** — the manager reviews during the 48-hour review period (Step 7). Exception: `split-suspect` is a **soft auto-deduction** (see below).

- **`split-suspect`**: 3+ S-tier PRs from the same author merged within 24 hours with related titles (shared prefix or keywords) — likely one deliverable split into micro-PRs. **Soft auto-deduction:** collapse the group into a single S payout (500 KES total instead of N × 500). Show in the report as `split-suspect: merged [N] PRs → 1 × S`. The manager can override during the review period with a one-line justification — but the default is collapsed.
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
| Author | S × 500 | M × 1,000 | L × 2,000 | XL × 3,500 | Gross (KES) | Revert Deductions | Net (KES) |

**Gross** = sum of (tier count × tier rate) for all feature PRs.

**Automatic Deductions:**
- `revert-pair` — both the original and the revert are excluded (zero net value)
- `split-suspect` — collapsed to 1 × S payout. Show the saving: e.g., "split-suspect: 3 PRs → 1 × S (saved 1,000 KES)"

All other flags are advisory — the manager decides during review.

**Net** = Gross minus revert-pair deductions.

Show a **monthly projection** only for windows of 14+ days:
| Author | Net (KES) | Window Days | Projected Monthly (KES) | Projected Monthly (USD @ 130) |
For windows under 14 days, show actuals only with a note: "Window too short for reliable monthly projection."

### 5g. Reviews Given
| Author | Reviews Given | Substantive Reviews (with comments) | Avg Review Turnaround (hours) |
Pull from `gh api` review data. This section is informational — review work is not bounty-compensated in v2 but is surfaced so the manager can factor it into payout decisions.

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
2. **`reports/payouts/balances.json`** (in the working repo) — append-only ledger of explicit advance agreements. Most months it's empty. Each entry has lifecycle: `pending` → `applied` (one or more periods) → `settled`. Each pending entry can include an `apply_when` condition (currently supports `gross >= NNNN`, `gross > NNNN`, etc.) that gates auto-application — useful when an advance shouldn't be drawn down until the engineer's monthly gross bounty crosses a threshold (so we don't compound assignment shortfalls). When the condition is met, the skill proposes applying the advance; when it isn't met, the engineer's statement renders a "carried forward" block explaining the rollover. The skill never auto-creates entries — manual edits welcome.
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
2. Filter to: authored by an active engineer (via `fizzy_user_id` map) within the analysis window AND on/after the engineer's `bounty_start_date` if set. (See "Per-engineer bounty start date" below.)
3. Classify each surface independently:
   - **Comment-based categories** (`ticket-review`, `pr-review`, `qa-handoff`, `manual-qa`): walk in priority order. A comment matches if it (a) meets `min_length`, (b) hits any of `detect_any` keywords, AND (c) hits all of `detect_all` clauses (each clause requires any of its keywords). Unmatched comments longer than `track_other_min_length` surface as "uncategorized" so the manager can refine the detectors.
   - **Card-creation categories** (`prod-triage`): when a category specifies `surface: card_creation`, scan card metadata instead of comments. Match if the card was created by the engineer's `fizzy_user_id`, on a board in the category's `boards` list, with a title hitting any of `title_detect_any`. Each matching card counts once at `rate_kes` regardless of how the engineer later updates it.
4. Sum per-engineer per-category: `count × rate_kes` = subtotal. Net ops = sum of all category subtotals.

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
- **QA (Elvis):** never gets a PR-based statement.
- **Engineers with PRs but no `engineers.yaml` entry:** team payout report counts their bounty; no statement file is written. The skill prints a one-line warning suggesting the user add them to `engineers.yaml` if they should be invoiced.

## Bounty Rate Reference

These rates are fixed in KES (Kenyan Shillings). They are intentionally conservative — the team is bootstrapped and operating in the East African market.

| Tier | Rate (KES) | ~USD @ 130 | Scope |
|------|-----------|------------|-------|
| S | 500 | ~$3.85 | Single, well-defined output with a clear finish line (bug fix, copy edit, UI tweak) |
| M | 1,000 | ~$7.70 | Complete deliverable with multiple steps or components (new feature, process doc) |
| L | 2,000 | ~$15.40 | Substantial end-to-end deliverable spanning multiple sessions (full feature, campaign, detailed report) |
| XL | 3,500 | ~$26.90 | High-judgment deliverable requiring significant planning, iteration, or cross-functional context (system architecture, go-to-market strategy, full product spec) |

### Role-specific notes

- **QA (Elvis/Much1r1):** QA work is measured by defect escape rate and test coverage, not PR volume. Elvis is excluded from the PR-based bounty table and tracked separately. If QA contributors submit code PRs, those are bounty-eligible like anyone else's.
- **New contributors (first 30 days):** Contributors in their first 30 days of activity are marked with a `ramping-up` tag. Their tier distribution is shown for context but the manager should expect S-heavy output during onboarding — this is normal, not underperformance.
- **Founder:** Tracked in a separate section for workload visibility. Not bounty-eligible (sweat equity).

## Implementation Notes

- Run all `gh pr list` commands in parallel (one per repo) for speed
- Fetch `gh pr view` data (files, reviews) only for PRs above S-tier threshold to avoid API rate limits
- Use Python for data processing — it handles JSON, dates, and table formatting well
- The analysis script is self-contained in a Python block. **Allowed deps: stdlib + `pyyaml`** (for parsing `repos.yaml`, `engineers.yaml`, `ops-rates.yaml`). Install with `pip3 install --quiet pyyaml` if missing.
- **Fizzy auth:** the `--pre-invoice` mode hits the Fizzy API for ops detection. Source the token from `.env.local` before running: `set -a && source <repo>/.env.local && set +a` — exposes `FIZZY_API_TOKEN` for the Python script to read via `os.environ`. See [.claude/rules/env-local-credentials.md](../../../../.claude/rules/env-local-credentials.md).
- **Fizzy API patterns:** use `urllib.request` (stdlib) with `Authorization: Bearer ${FIZZY_API_TOKEN}` and `User-Agent: VettedAI/1.0`. Always append `.json` to action endpoints. See [.claude/rules/fizzy-api-patterns.md](../../../../.claude/rules/fizzy-api-patterns.md). Parallelize card-fetches via `ThreadPoolExecutor(max_workers=25)` — ~10 seconds for 800-card scan.
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
| Bounty (PRs) | `gh pr list` across `repos.yaml` | Merged PRs into integration branches, tiered S/M/L/XL by lower of files/lines |
| Ops contributions | Fizzy comments + card creations across `ops-rates.yaml > boards` | pr-review, qa-handoff, ticket-review, manual-qa (comments) + prod-triage (card creations) |
| Advances | `reports/payouts/balances.json` | Explicit advance agreements, lifecycle pending → applied → settled |
| Per-engineer eligibility | `engineers.yaml` `bounty_start_date` | Filter applied to PRs / comments / card creations: `event_date >= bounty_start_date` |
