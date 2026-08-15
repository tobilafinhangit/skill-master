---
name: generating-release-notes
description: >
  Use when a batch of engineering work is complete. Generates team-readable
  release notes OR polished community-facing newsletter content from git
  history. Supports internal (default), newsletter, or both output modes.
version: 2.2.0
license: MIT
metadata:
  author: VettedAI
  category: communication
  tags: [release-notes, changelog, newsletter, community, team-communication, qa, product]
  created: 2026-02-18
  updated: 2026-07-31
argument-hint: "[date-range or commit-range] [newsletter|both]"
---
> **Note:** This skill references `.claude/rules/*.md` files from the original author's private repos — optional deep-dive context, not required. If those files aren't present in your repo, follow the inline instructions in this skill directly.


# Generating Release Notes

Produces team-readable release notes and/or polished community-facing newsletter content from git history. Internal notes bridge commits to QA and stakeholders. Newsletter mode generates changelog content suitable for community distribution (think: Linear's changelog, Vercel's ship updates).

## When to Use

- After completing a batch of features (end of sprint, weekly cadence)
- Before QA testing begins on a staging branch
- When stakeholders ask "what shipped this week?"
- When you want to announce shipped features to the community
- Before sending a weekly/biweekly product update email or changelog post
- When marketing or community team asks "what can we announce?"
- Explicitly via `/generating-release-notes`

## Why This Exists

Commits are developer-facing. Product, QA, and stakeholders need:
- **What changed** in plain English
- **Where to find it** (navigation path in the app)
- **Why it matters** (ties back to feedback or business goals)
- **What to test** (verification steps, edge cases)

The community needs something different — polished, benefit-led updates that celebrate what shipped and help users discover new features.

## Inputs

The skill accepts a range. If none provided, ask which:

| Input | Example | Use When |
|-------|---------|----------|
| Date range | `last 7 days`, `since Feb 10` | Weekly cadence |
| Commit range | `abc123..HEAD` | After a specific batch |
| Tag/branch | `since v1.2.0`, `main..staging` | Release-based workflow |
| Plan file | path to `.claude/plans/*.md` | When detailed plans exist |

### Output Mode

Append a mode keyword to your invocation:

| Keyword | Behavior |
|---------|----------|
| *(none)* | Internal release notes only (default, backward-compatible) |
| `newsletter` | Community-facing newsletter only |
| `both` | Generates both internal notes and newsletter |

Examples:
- `/generating-release-notes last 7 days` — internal notes
- `/generating-release-notes since v1.2.0 newsletter` — newsletter
- `/generating-release-notes last 7 days both` — both outputs

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

### Step 3: Write Entries

#### 3a: Internal Mode (default)

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

#### 3b: Newsletter Mode

For each **user-visible** change (skip INTERNAL category entirely), write:

```markdown
### [Emoji] [Feature Name in 3-6 Words]

[1-2 sentence "Now you can..." or "We shipped..." framing. Lead with the user
benefit, not the technical change.]

[Optional: Before/after comparison if the change modifies existing behavior]

<!-- SCREENSHOT: [Description of what to capture — e.g., "the new booking link
field on the profile page"] -->

---
```

**Newsletter writing rules:**
- **Lead with benefit, not mechanism.** "You can now add your Calendly link to your profile" not "Added booking_url column to participants table"
- **Use "Now you can..." or "We shipped..." framing.** These are action-oriented and put the user in the driver's seat.
- **One emoji per feature.** Pick from: ✨ (new), ⚡ (improvement), 🔧 (fix), 🎯 (precision/targeting), 📧 (email/comms), 🤝 (connection/matching), 📅 (scheduling). No emoji salad.
- **Screenshot placeholders are mandatory** for any visual change. Use HTML comments so they're invisible in rendered markdown but obvious in the source.
- **Skip INTERNAL changes entirely.** The community doesn't care about refactors, dependency bumps, or infra changes.
- **Skip bug fixes that the community never saw.** If a bug was introduced and fixed within the same release window, omit it. Only include fixes for bugs the community actually experienced.

### Step 4: Compile the Document

#### 4a: Internal Template (default)

Use this template:

```markdown
# Release Notes — [Date or Version]

**Branch:** `[branch-name]`
**Commits:** [count] ([range])
**Key areas:** [1-3 word summary of main areas touched]

---

## User-Facing Changes

### New Features

[Entries from Step 3a]

### Improvements

[Entries from Step 3a]

### Bug Fixes

[Entries from Step 3a]

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

#### 4b: Newsletter Template

Use this template:

```markdown
# [Catchy Title — 5-8 words, no version numbers]

*[Date in human format, e.g., "March 15, 2026"]*

**TL;DR** — Here's what shipped this week:
- [Bullet 1 — most impactful feature, 1 line]
- [Bullet 2]
- [Bullet 3]
- [Up to 5 bullets max]

---

[Feature spotlight entries from Step 3b, ordered by impact — biggest first]

---

## Try It Out

[1-2 sentences pointing to the app or specific feature. Include a direct link
if possible.]

**[CTA button text] →** `[URL]`

---

*Shipped with ☕ by the [team name]*
*Questions? Reply to this email or drop us a note at [contact]*
```

**Title guidelines:**
- Confident, not clickbait. "Smarter Matching, Easier Scheduling" not "YOU WON'T BELIEVE what we shipped"
- No version numbers. Community doesn't care about v1.3.2.
- Action-oriented or benefit-oriented. "Book Coffee Chats in One Click" not "Release 47"

**TL;DR guidelines:**
- 3-5 bullets, each one line
- Start each bullet with a verb: "Added", "Improved", "Fixed", "Enabled"
- Most impactful item first

### Step 5: Output

#### 5a: Internal Mode

Write to `docs/release-notes/[YYYY-MM-DD].md` (create directory if needed).

If the user prefers a different location, ask once and remember.

#### 5b: Newsletter Mode

Write to `docs/changelog/[YYYY-MM-DD].md` (create directory if needed).

#### 5c: Both Mode

Write both files. Generate the newsletter *after* the internal notes, since the internal notes serve as the comprehensive source of truth that the newsletter distills from.

After writing, remind the team:
> **Next steps:** Review the newsletter draft, fill in screenshot placeholders (marked with `<!-- SCREENSHOT: ... -->`), and send via your distribution channel.

## Quality Checklist

### Internal Notes

Before delivering:
- [ ] Every commit is accounted for (nothing silently dropped)
- [ ] No code jargon in user-facing sections (function names, file paths)
- [ ] Navigation paths are accurate ("Workspace > New Project > Step 3", not "ReviewRoleDNA.tsx")
- [ ] QA checklist is actionable (someone unfamiliar with the code could follow it)
- [ ] Deployment notes included if edge functions, migrations, or env changes are needed
- [ ] Document is copy-pasteable into Slack/Notion without formatting issues

### Newsletter

Before delivering the newsletter draft:
- [ ] INTERNAL changes are excluded entirely
- [ ] No code jargon anywhere (no function names, file paths, column names)
- [ ] Every visual change has a `<!-- SCREENSHOT: ... -->` placeholder
- [ ] TL;DR has 3-5 bullets, each starting with a verb
- [ ] Title is 5-8 words, no version numbers
- [ ] Benefits lead every feature entry (not mechanisms)
- [ ] CTA points to a real, working URL
- [ ] Voice check: read it aloud — does it sound like a person, not a press release?
- [ ] Bug fixes only included if the community actually experienced the bug
- [ ] Sign-off is present

## Anti-Patterns

### Internal Notes

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

### Newsletter

**The corporate press release:**
```markdown
# BAD
We are excited to announce the release of VFA Coffee Chat v1.3.2, which
includes several new features and improvements designed to enhance the
user experience.

# GOOD
# Smarter Matches, Easier Scheduling
Here's what shipped this week — booking links, better follow-ups, and
a cleaner match experience.
```

**The technical leak:**
```markdown
# BAD
We added a booking_url column to the participants table and updated the
edge function to include it in the mutual intro email template.

# GOOD
✨ Add your Calendly or booking link to your profile — your match will
see it right in their intro email, so scheduling is one click away.
```

**The invisible fix:**
```markdown
# BAD
Fixed a race condition where duplicate automations could be created when
the cron job overlapped with a manual trigger.

# GOOD
(Omit entirely — the community never saw this bug. If they did:)
🔧 Fixed an issue where some participants received duplicate follow-up
emails. Sorry about the inbox clutter!
```

**Screenshot-less visual changes:**
```markdown
# BAD
We redesigned the match card on the My Matches tab.

# GOOD
✨ Refreshed Match Cards
Your matches page got a visual upgrade — cleaner layout, your partner's
role and LinkedIn at a glance.

<!-- SCREENSHOT: My Matches tab showing the new match card with role
badge and LinkedIn link visible -->
```

**The feature dump:**
```markdown
# BAD — listing 15 minor changes with equal weight
- Updated button color
- Changed font size on mobile
- Added aria labels
- ...

# GOOD — consolidate into a single entry or omit
⚡ Polish Pass
Small visual refinements across the app — cleaner buttons, better mobile
spacing, and improved accessibility.
```

## Newsletter Voice Guide

The newsletter voice is **confident builder** — a team that ships fast, cares about its community, and communicates like humans.

| Do | Don't |
|----|-------|
| "We shipped smarter matching this week" | "We are pleased to announce..." |
| "Now you can add your Calendly link" | "A new field has been added to the database" |
| "Fixed an issue where follow-up emails arrived late" | "Resolved a race condition in the automation scheduler cron job" |
| "Your coffee chats just got easier to schedule" | "We have implemented booking URL integration" |
| Name the benefit in the first sentence | Lead with technical details |
| Use "we" and "you" | Use passive voice or third person |

**Tone calibration:**
- More Linear changelog, less enterprise release notes
- More "shipped it" energy, less "please find attached"
- Warm but not cutesy. Professional but not corporate.
- Celebrate shipping without being breathless about it

**Brand alignment:**
- The product connects people. Language should reflect human connection.
- Use product-specific metaphors sparingly — once in sign-off is fine, not in every heading.
- Reference the community ("your match", "your profile") not the system ("the matching algorithm", "the pairing engine").

## Tips

- **Plan files are gold.** If `.claude/plans/` has a plan for this work, read it. Plans contain the "why" and "what to verify" that commit messages lack.
- **Ask about context.** If commits reference a person's feedback (e.g., "Lemuel @ APP"), include that attribution — it helps the team trace decisions.
- **Weekly > per-push.** Small daily commits create noise. Batch into weekly summaries.
- **Err on the side of too much QA detail.** Testing notes that are too specific are better than vague "test it works."
- **Newsletter is a distillation, not a translation.** Don't convert every internal entry to newsletter format. Pick the 3-7 most impactful user-facing changes. A shorter, punchier newsletter beats a comprehensive one.
- **Generate internal notes first, then newsletter.** The internal notes are your source of truth. The newsletter cherry-picks from them.
- **Screenshot placeholders save review cycles.** Describing exactly what to capture ("the profile page with the new booking link field filled in") means the person adding screenshots doesn't need to guess.
- **One newsletter per week max.** Even if you ship daily, batch into weekly updates. Community attention is finite.

### Step 6: Post the Full Release Notes to Fizzy

After writing release notes (any mode), create a card on the project's **Fizzy board** containing the complete internal release notes. The Fizzy card is the team-facing release artifact; the Markdown file in `docs/release-notes/` is its repository copy.

**Do not condense the card into a summary or replace its QA detail with a link to the local file.** Convert the complete internal note to HTML and include every release entry, including its Where, What, Why, and Test fields, as well as Internal Changes, the full QA Checklist, and Deployment Notes. This is the default even when the user simply asks for “release notes” or a “summary” on Fizzy.

If the user explicitly asks for a shorter executive summary, create that as a separate companion card or comment; do not overwrite or abbreviate the full release-notes card.

#### Fizzy Board Config (per-project)

Each project must define these values. Look in these locations (in order): `.claude/rules/fizzy-api-patterns.md`, memory files, `qa-handoff` skill, or the fizzy skill's `SKILL.md` for the board ID. The token is always in the project's `.env.local` as `FIZZY_API_TOKEN`.

| Field | Where to find |
|-------|---------------|
| Account ID | `{FIZZY_ACCOUNT_ID}` (your Fizzy account slug) |
| Board ID | Project-specific — check CLAUDE.md, memory, or fizzy skill |
| Token | `.env.local` as `FIZZY_API_TOKEN` (path varies per project) |
| Endpoint | `POST https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/{BOARD_ID}/cards.json` |

**Important:** Always use `.json` suffix on the endpoint and include `User-Agent: VettedAI/1.0` header — without these Fizzy returns 401/422.

#### Card Format

- **Title:** `Release Notes — [Date] ([N] commits)`
- **Body:** Complete internal release notes as HTML (use the `description` field — Fizzy ignores `content`). Preserve the same content and order as the Markdown internal note:
  - `<h2>User-Facing Changes</h2>` with New Features, Improvements, and Bug Fixes.
  - Every entry must include **Where**, **What**, **Why** (when known), and **Test**; do not reduce these to one-line bullets.
  - `<h2>Internal Changes</h2>` with all relevant internal entries.
  - `<h2>QA Checklist</h2>` with every actionable checkbox from the Markdown note.
  - `<h2>Deployment Notes</h2>` when applicable, including migrations, Edge Functions, env vars, crons, and new endpoints.
- **Rendering:** Convert the finished Markdown document to HTML or generate equivalent HTML directly. Verify the card body contains the complete QA checklist and detailed entry text before reporting success.

#### Posting

Use Python for reliable JSON encoding (HTML in shell strings is fragile):

```python
python3 << 'PYEOF'
import json, subprocess

body_html = """<h3>New Features</h3><ul><li>...</li></ul>..."""

payload = json.dumps({"card": {
    "title": "Release Notes — YYYY-MM-DD (N commits)",
    "description": body_html  # NOTE: Fizzy uses 'description', NOT 'content'
}})

result = subprocess.run([
    "curl", "-s", "-i", "-X", "POST",
    "https://app.fizzy.do/{FIZZY_ACCOUNT_ID}/boards/{BOARD_ID}/cards.json",
    "-H", "Authorization: Bearer {TOKEN}",
    "-H", "User-Agent: VettedAI/1.0",
    "-H", "Content-Type: application/json",
    "-d", payload
], capture_output=True, text=True)
print(result.stdout[:500])
PYEOF
```

Extract the card number from the `Location` header (e.g., `/{FIZZY_ACCOUNT_ID}/cards/500.json` → card #500). Report the card number to the user when done.

#### If board details are unknown

If you can't find the Fizzy board ID for the current project, ask the user:
> "Which Fizzy board should I post release notes to? I need the board ID (e.g., `03f58rc5c48jorujpxqp5da5b`)."
