---
name: learning-from-corrections
description: Use after bug fixes or corrections to update CLAUDE.md with learned anti-patterns. Invoke after fixing mistakes to build project memory.
version: 1.0.0
---

# Learning from Corrections

Extracts lessons from mistakes and updates CLAUDE.md to prevent recurrence.

## When to Use
- After fixing a bug
- After correcting wrong code
- When user says "that was wrong" or "remember this"
- Explicitly via `/learning-from-corrections`

## Workflow

### Step 1: Identify the Mistake
If not clear from conversation context, ask:
- What was the incorrect code/approach?
- What made it wrong?

### Step 2: Identify the Correction
- What's the correct pattern?
- Why does it work?

### Step 3: Categorize
Determine which section in CLAUDE.md:
- React/TypeScript
- Supabase Edge Functions
- Database/SQL
- API Integration
- [Create new section if needed]

### Step 4: Format Anti-Pattern

Use this template:
```
**[Brief description]:**
```[language]
// ❌ WRONG - [why it's wrong]
[incorrect code]

// ✅ CORRECT - [why it works]
[correct code]
```
```

### Step 5: Update CLAUDE.md

1. Read current `/CLAUDE.md`
2. Find the appropriate "Anti-Patterns" subsection
3. Append the new entry under the correct category
4. If category doesn't exist, create it

### Step 6: Log Session Notes (Optional)

If `/.claude/notes/` directory exists:
1. Find or create today's notes file: `YYYY-MM-DD-*.md`
2. Add detailed context about the fix
3. Include: file paths, line numbers, root cause analysis

## Example

**Conversation context:** Fixed `onClick={() => handleFn}` bug

**Action:** Add to CLAUDE.md under "React/TypeScript" section:

```markdown
**Event Handlers:**
```tsx
// ❌ WRONG - Returns function reference, never calls it
onClick={() => handleRecalculateRankings}

// ✅ CORRECT - Direct reference (React calls it on click)
onClick={handleRecalculateRankings}
```
```

## Quality Checklist
Before completing, verify:
- [ ] Anti-pattern is specific (not generic advice)
- [ ] Code examples are from the actual fix (not hypothetical)
- [ ] Category matches the technology/domain
- [ ] CLAUDE.md was successfully updated
- [ ] Entry follows existing format in CLAUDE.md

## Important
- Keep entries concise - focus on the pattern, not the story
- Use real code from the conversation, not sanitized examples
- If the same pattern already exists in CLAUDE.md, don't duplicate
- Link to session notes for detailed context if needed
