---
name: skill-strategist
description: Analyzes user problems to recommend existing skills from the repository or design new ones based on available resources. Use when the user wants to solve a problem but doesn't know which skill to use, or when proposing a new skill.
---

# Skill Strategist

Your role is to be the "Librarian" and "Architect" of the Antigravity skill ecosystem. You connect user problems to available tools, avoiding redundant work and ensuring high-leverage skill creation.

## When to Use This Skill
- The user asks "Do we have a skill for X?"
- The user has a complex problem and needs advice on which tools to use.
- The user proposes building a new skill, and you need to verify if it's necessary.
- You want to explore `wsboson-agents` or `superpowers` to see what capabilities are valid.

## Resources
- **Active Skills**: `.agent/skills/` (Master source), which are mirrored to `.cursor/skills` and `.claude/skills` for cross-IDE compatibility.
- **Core Skills**: `superpowers/skills/` (High-quality, ready to copy)
- **Knowledge Base**: `wsboson-agents/plugins/` (Vast library of patterns and templates)

## Process

### Phase 1: Context Analysis
**Goal**: Understand the *real* problem, not just the requested solution.
1.  **Analyze Request**: What is the user trying to achieve? (e.g., "Fix a bug" -> Troubleshooting. "Deploy app" -> CI/CD).
2.  **Identify Keywords**: Extract technical terms (e.g., "Postgres", "AWS", "React", "Testing").

### Phase 2: Inventory Check
**Goal**: Find if we already have the tool.
1.  **Check Active**: Is there a relevant skill in `.agent/skills`?
2.  **Check Core**: Look in `superpowers/skills`. (e.g., `writing-plans`, `troubleshooting`).
3.  **Check Knowledge Base**: Look in `wsboson-agents/plugins`. (This is a goldmine for specific domains like `kubernetes-operations` or `database-migrations`).

### Phase 3: Strategize & Brainstorm
**Goal**: Engage the user to select the best path.
*Do not immediately build. Discuss first.*

**Scenario A: Exact Match Found**
- **Action**: "I found an existing skill `[Name]` in `[Location]`. It handles exactly what you need. Shall we use/install it?"

**Scenario B: Strong Foundation Found**
- **Action**: "We don't have a dedicated skill, but `wsboson-agents/plugins/[Category]` contains 80% of what we need. I recommend we create a new skill `[New Name]` based on those patterns. Thoughts?"

**Scenario C: No Match (Greenfield)**
- **Action**: "This looks like a novel problem. We should build a custom skill. Let's define the scope."

### Phase 4: Skill Proposal (If Building New)
If a new skill is required, create a brief proposal artifact before coding:
```markdown
# Skill Proposal: [Name]
**Goal**: [One sentence objective]
**Source Material**: [List files/folders in wsboson-agents/superpowers to use as reference]
**Why**: [Brief justification for why existing skills aren't enough]
```

## Instructions for Use
1.  **Start by exploring**: Use `list_dir` on the resource directories if you haven't recently.
2.  **Present Options**: Give the user a choice between "Quick Fix" (use existing) and "Long Term Asset" (build new).
3.  **Advocate for Reuse**: Always prefer adapting trusted patterns from `superpowers` over inventing from scratch.
