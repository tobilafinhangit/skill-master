---
name: generating-release-notes
description: Use when a batch of engineering work is complete and the team needs a summary of what shipped. Generates team-readable release notes from git history, grouped by audience impact, with navigation paths and QA testing notes.
version: 1.0.0
license: MIT
metadata:
  author: VettedAI
  category: communication
  tags: [release-notes, changelog, team-communication, qa, product]
  created: 2026-02-18
argument-hint: "[date-range or commit-range]"
---

# Generating Release Notes

Produces team-readable release notes from git history that bridge the gap between engineering commits and feature discoverability for product, QA, and stakeholders.

## When to Use

- After completing a batch of features (end of sprint, weekly cadence)
- Before QA testing begins on a staging branch
- When stakeholders ask "what shipped this week?"
- Explicitly via `/generating-release-notes`

## Why This Exists

Commits are developer-facing. Product, QA, and stakeholders need:
- **What changed** in plain English
- **Where to find it** (navigation path in the app)
- **Why it matters** (ties back to feedback or business goals)
- **What to test** (verification steps, edge cases)

## Inputs

The skill accepts a range. If none provided, ask which:

| Input | Example | Use When |
|-------|---------|----------|
| Date range | `last 7 days`, `since Feb 10` | Weekly cadence |
| Commit range | `abc123..HEAD` | After a specific batch |
| Tag/branch | `since v1.2.0`, `main..staging` | Release-based workflow |
| Plan file | path to `.claude/plans/*.md` | When detailed plans exist |

## Workflow

### Step 1: Gather Raw Material

```bash
# Get commits for the range
git log --oneline --no-merges <range>

# Get full diff stats for scope understanding
git diff --stat <range>

# Get detailed commit messages (the body often has context)
git log --format="%h %s%n%b%n---" <range>
```

If plan files exist in `.claude/plans/`, read them — they contain the *why* behind changes and are richer than commit messages.

### Step 2: Classify Changes

Group every change into exactly one category:

| Category | Icon | Criteria |
|----------|------|----------|
| New Features | **NEW** | Functionality that didn't exist before |
| Improvements | **IMPROVED** | Enhancements to existing functionality |
| Bug Fixes | **FIXED** | Corrections to broken behavior |
| Internal | **INTERNAL** | Refactors, tooling, infra — no user-visible change |

**Rule:** If a commit touches both a bug fix and an improvement, classify by the *primary intent*.

### Step 3: Write Each Entry

For each change, write:

```markdown
**[Category]** Short description in user-facing language

- **Where:** Navigation path to find it (e.g., Workspace > New Project > Step 3)
- **What:** 1-2 sentences explaining the change from a user's perspective
- **Why:** The feedback, ticket, or problem that prompted this (if known)
- **Test:** How QA can verify this works (specific steps)
```

**Writing rules:**
- Use the user's language, not code language
  - YES: "Weight sliders now snap to 10% increments"
  - NO: "Updated adjustWeightsProportionally() to round to nearest 10"
- Include the navigation path so anyone can find the feature
- Testing notes should be specific enough for someone unfamiliar with the code

### Step 4: Compile the Document

Use this template:

```markdown
# Release Notes — [Date or Version]

**Branch:** `[branch-name]`
**Commits:** [count] ([range])
**Key areas:** [1-3 word summary of main areas touched]

---

## User-Facing Changes

### New Features

[Entries from Step 3]

### Improvements

[Entries from Step 3]

### Bug Fixes

[Entries from Step 3]

---

## Internal Changes

[Entries that don't affect users — optional, collapse if many]

---

## QA Checklist

A consolidated testing checklist extracted from individual entries:

- [ ] [Test item 1]
- [ ] [Test item 2]
- ...

---

## Deployment Notes

[Any edge functions to deploy, migrations to run, env vars to set, etc.]
Only include this section if there are actual deployment steps beyond "merge and deploy."
```

### Step 5: Output

Write the document to `docs/release-notes/[YYYY-MM-DD].md` (create directory if needed).

If the user prefers a different location, ask once and remember.

## Quality Checklist

Before delivering:
- [ ] Every commit is accounted for (nothing silently dropped)
- [ ] No code jargon in user-facing sections (function names, file paths)
- [ ] Navigation paths are accurate ("Workspace > New Project > Step 3", not "ReviewRoleDNA.tsx")
- [ ] QA checklist is actionable (someone unfamiliar with the code could follow it)
- [ ] Deployment notes included if edge functions, migrations, or env changes are needed
- [ ] Document is copy-pasteable into Slack/Notion without formatting issues

## Anti-Patterns

**Commit-message parroting:**
```markdown
# BAD - Just reformatting git log
- feat(wizard): Improve Role Summary and Role DNA pages
- fix(admin): Fix broken search

# GOOD - User-facing language with context
**IMPROVED** Role DNA page now lets you edit AI classifications
- **Where:** Workspace > New Project > Step 3 (Review Role DNA)
- **What:** Role Classification (formerly "Role Context") is now editable.
  You can override the AI-assigned role family, seniority, and context flags.
- **Why:** Feedback from Lemuel — all AI-generated content should be user-overridable
- **Test:** Click Edit on Role Classification > change role family > Save > verify warning toast appears
```

**Missing the "where":**
```markdown
# BAD - User can't find the feature
Weight sliders now increment by 10%.

# GOOD - User knows exactly where to look
**IMPROVED** Weight sliders snap to 10% increments (min 10%, max 50%)
- **Where:** Workspace > New Project > Step 3 > Performance Dimension Weights
```

**Over-including internals:**
```markdown
# BAD - QA doesn't need to know about refactors
- Moved snapWeightsToGrid() helper function
- Updated useEffect dependency arrays

# GOOD - Only mention if it affects testing
(Omit entirely — internal refactors don't go in user-facing sections)
```

## Tips

- **Plan files are gold.** If `.claude/plans/` has a plan for this work, read it. Plans contain the "why" and "what to verify" that commit messages lack.
- **Ask about context.** If commits reference a person's feedback (e.g., "Lemuel @ APP"), include that attribution — it helps the team trace decisions.
- **Weekly > per-push.** Small daily commits create noise. Batch into weekly summaries.
- **Err on the side of too much QA detail.** Testing notes that are too specific are better than vague "test it works."
