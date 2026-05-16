---
name: learning-from-corrections
description: Use after bug fixes or corrections to update .claude/rules/ with learned anti-patterns and add a one-liner to the CLAUDE.md index table. Invoke after fixing mistakes to build project memory. Every run also prunes stale rules so the set stabilizes instead of growing unbounded.
version: 2.1.0
---

# Learning from Corrections

Extracts lessons from mistakes and writes them to `.claude/rules/` files. Keeps CLAUDE.md as a slim index.

## When to Use
- After fixing a bug
- After correcting wrong code
- When user says "that was wrong" or "remember this"
- Explicitly via `/learning-from-corrections`
- To prune drift even with no new lesson — run it and let Step 7 do a retirement pass

## Workflow

### Step 0: Bootstrap (first run only)
If `.claude/rules/` directory doesn't exist:
1. Create `.claude/rules/` directory
2. Check if CLAUDE.md has a `## Key Rules` table — if not, append one:
```markdown

## Key Rules (details in `.claude/rules/`)

| Rule | One-liner | File |
|------|-----------|------|
```
This makes the skill work in any project, even if it hasn't been converted to the rules structure yet.

### Step 1: Identify the Mistake
If not clear from conversation context, ask:
- What was the incorrect code/approach?
- What made it wrong?

### Step 2: Identify the Correction
- What's the correct pattern?
- Why does it work?

### Step 3: Choose a Rule Name
1. Pick a kebab-case name describing the anti-pattern (e.g., `event-handler-refs`)
2. Check if `.claude/rules/{name}.md` already exists — if so, **update** it instead of creating a duplicate
3. Skip if the pattern is generic platform knowledge (not project-specific)

### Step 4: Write Rule File

Create `.claude/rules/{name}.md` using this template:

```markdown
# [Title]

## Rule
[One-sentence imperative — what to always/never do]

## Wrong
```[language]
// [why it's wrong]
[incorrect code from the actual fix]
```

## Right
```[language]
// [why it works]
[correct code from the actual fix]
```

## Context
[2-4 sentences: why this matters, what breaks, cascade effects]

## Affected Files
- [file1]
- [file2]
```

### Step 5: Add One-Liner to CLAUDE.md Table

1. Read current `/CLAUDE.md`
2. Find the `## Key Rules` table
3. Add ONE new row: `| Rule name | One-liner summary | \`{name}.md\` |`
4. **NEVER** add code blocks, full anti-pattern sections, or more than one line to CLAUDE.md

### Step 6: Log Session Notes (Optional)

If `/.claude/notes/` directory exists:
1. Find or create today's notes file: `YYYY-MM-DD-*.md`
2. Add detailed context about the fix
3. Include: file paths, line numbers, root cause analysis

### Step 7: Prune Pass (every run — not optional)

Adding without retiring is the drift engine. Run this **every** invocation, even when no new rule was written. It is read-only until the user confirms — never delete a rule unprompted (rules are durable, version-controlled, human-reviewed artifacts).

1. **Scan for stale candidates** using these signals. They are *coarse* — every hit is a question for the user, never a conclusion. The dry-run that motivated this step produced ~100% false positives from naive versions of these checks; the qualifiers below are mandatory, not optional:

   - **Dead path** — flag only when **all** of a rule's `## Affected Files` are: (a) concrete repo paths (not globs, not prose like "Any webhook handler"), **and** (b) *in this checkout's repo* (a path under another repo — `backend-restructing/`, `congrats/` when not present — is NOT missing, it's cross-repo; skip it), **and** (c) not qualified with "(or equivalent)", "reference implementation", "e.g.", "example" (those are illustrative pointers, not the rule's load-bearing target), **and** (d) genuinely absent (`test -e`). Even then: a dead path usually means *fix the pointer*, not retire the rule — only propose retire if the rule's imperative itself is moot without those files.
   - **Story-only rule** — do NOT keyword-match for imperative verbs (a fixed allowlist misses "Invalidate", "Force", "Save", … and false-flags solid rules). Instead read the `## Rule` section and judge semantically: does it state an enforceable directive (any imperative mood / "do X / never Y / prefer Z")? Only if it contains *no* directive at all and is purely recounting an incident → **trim** candidate (step 3).
   - **Superseded/duplicate** — another rule's `## Rule` covers the same imperative, or two imperatives directly conflict. Merge/retire candidate. Overlap in *topic* is not duplication; the imperatives must actually coincide or contradict.
   - **Heavy dated narrative is NOT itself a signal.** A high count of dates/PR refs only matters if the underlying incident is *no longer live* (e.g. a cutover that has completed, a migration fully rolled out) AND the standing imperative is separable from the story. A brand-new rule, or one whose incident is still in-flight, is rich-by-design — leave it.
   - Age alone, "references a merged PR" alone, or "long file" alone are **never** signals. Durable standards routinely cite the incident that birthed them.

2. **Present a table, decide nothing unilaterally:**

   | Rule | Signal | Recommended action |
   |------|--------|--------------------|
   | `foo-bar.md` | Affected files all deleted | Retire |
   | `baz.md` | Conflicts with `qux.md` §Rule | Merge into `qux.md` |
   | `old-incident.md` | Story-only, no imperative | Trim story → `.claude/notes/`, keep Rule/Wrong/Right |

   Ask the user to confirm per-row. Only on explicit confirmation: delete the rule file, remove its CLAUDE.md index row, and (for "Trim") move the dated narrative into a `.claude/notes/YYYY-MM-DD-*.md` entry while leaving the imperative + Wrong/Right in the rule.

3. **Trim, don't just delete.** The common case is a good standing rule buried in incident prose. Keep the imperative `## Rule` + `## Wrong`/`## Right`; relocate the "story" (dates, PR #s, who was affected) to `.claude/notes/`. The rule stays load-bearing; per-session context shrinks.

4. If the user declines all rows, that's fine — the value is the *surfaced list*, not forced deletion. Note "prune pass: N candidates surfaced, 0 actioned (user deferred)" so the next run re-surfaces them.

**Never** retire a rule whose imperative is still enforceable just because its originating PR merged. **Never** batch-delete. **Never** touch `.claude/rules/` outside the confirmed rows.

## Example

**Conversation context:** Fixed `onClick={() => handleFn}` bug

**Action 1:** Create `.claude/rules/event-handler-refs.md`:
```markdown
# Event Handler Refs

## Rule
Pass event handlers as direct references, not wrapped in arrow functions that return them.

## Wrong
```tsx
// Returns function reference, never calls it
onClick={() => handleRecalculateRankings}
```

## Right
```tsx
// Direct reference (React calls it on click)
onClick={handleRecalculateRankings}
```

## Context
Wrapping a handler in an arrow function without calling it (`() => fn` vs `() => fn()`) returns the function object instead of invoking it. The click does nothing.

## Affected Files
- Components with onClick handlers
```

**Action 2:** Add row to CLAUDE.md table:
```
| Handler refs | Pass handlers as direct refs, not `() => handler` | `event-handler-refs.md` |
```

## Quality Checklist
Before completing, verify:
- [ ] Rule file created/updated in `.claude/rules/`
- [ ] Anti-pattern is specific (not generic advice)
- [ ] Code examples are from the actual fix (not hypothetical)
- [ ] CLAUDE.md only has a new table row (no code blocks added)
- [ ] No duplicate — checked existing rules first
- [ ] Prune pass (Step 7) ran — stale/story-only/conflicting candidates surfaced to the user (even if 0 actioned)

## Important
- **NEVER** append code blocks to CLAUDE.md — all detail goes in `.claude/rules/`
- Skip generic platform knowledge (e.g., "Supabase SQL Editor returns one result") — only record project-specific patterns
- Keep entries concise — focus on the pattern, not the story
- Use real code from the conversation, not sanitized examples
- If the same pattern already exists in `.claude/rules/`, update it instead of creating a new file
- The prune pass (Step 7) is **not optional and not destructive-by-default** — surface candidates every run, delete only on explicit per-row confirmation. A learn-only loop with no retirement is exactly what makes the rule set drift into context bloat.
