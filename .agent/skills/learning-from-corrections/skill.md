---
name: learning-from-corrections
description: Use after bug fixes or corrections to update .claude/rules/ with learned anti-patterns and add a one-liner to the CLAUDE.md index table. Invoke after fixing mistakes to build project memory.
version: 2.0.0
---

# Learning from Corrections

Extracts lessons from mistakes and writes them to `.claude/rules/` files. Keeps CLAUDE.md as a slim index.

## When to Use
- After fixing a bug
- After correcting wrong code
- When user says "that was wrong" or "remember this"
- Explicitly via `/learning-from-corrections`

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

## Important
- **NEVER** append code blocks to CLAUDE.md — all detail goes in `.claude/rules/`
- Skip generic platform knowledge (e.g., "Supabase SQL Editor returns one result") — only record project-specific patterns
- Keep entries concise — focus on the pattern, not the story
- Use real code from the conversation, not sanitized examples
- If the same pattern already exists in `.claude/rules/`, update it instead of creating a new file
