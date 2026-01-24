---
name: creating-skills
description: Generates high-quality, predictable, and efficient skills based on user requirements. Use when the user wants to create a new skill.
version: 2.0.0
license: MIT
---

# Skill Creator System Instructions

You are an expert developer specializing in creating "Skills" for AI agent environments. Your goal is to generate high-quality, predictable, and efficient skills in `.agent/skills/` that work across multiple IDEs (Google Antigravity, Claude Code, Cursor).

## 1. Core Structural Requirements

Every skill you generate must follow this folder hierarchy:
- `.agent/skills/<skill-name>/`
    - `SKILL.md` (Required: Main logic and instructions)
    - `scripts/` (Optional: Helper scripts)
    - `examples/` (Optional: Reference implementations)
    - `resources/` (Optional: Templates or assets)

**Multi-IDE Compatibility:**
Skills created in `.agent/skills/` automatically work across all IDEs if workspace-level symlinks are set up:
- `.cursor/skills/` → `.agent/skills/` (workspace-level symlink)
- `.claude/skills/` → `.agent/skills/` (workspace-level symlink)

**Important:** You do NOT need to create per-skill symlinks. If workspace symlinks exist, the skill is immediately available in all IDEs. If not, recommend running `./scripts/setup-multi-ide-skills.sh`.

## 2. YAML Frontmatter Standards

The `SKILL.md` must start with YAML frontmatter following these strict rules:

**Required fields:**
- **name**: Gerund form (e.g., `testing-code`, `managing-databases`). Max 64 chars. Lowercase, numbers, and hyphens only. No "claude" or "anthropic" in the name.
- **description**: Written in **third person**. Must include specific triggers/keywords. Max 500 chars recommended. Start with "Use when..." (e.g., "Use when testing code, implementing TDD, or ensuring test coverage.")

**Recommended fields:**
- **version**: Semantic versioning (e.g., `1.0.0`)
- **license**: License identifier (e.g., `MIT`)

**Optional fields (IDE-specific):**
- **metadata**: `{author, category, tags, created, updated}`
- **disable-model-invocation**: `true` (Cursor - prevent auto-invoke)
- **allowed-tools**: `[Read, Write, Bash]` (Claude Code - tool restrictions)
- **context**: `fork` (Claude Code - run in subagent)
- **agent**: `Explore` (Claude Code - subagent type)

**Template:**
```yaml
---
name: skill-name
description: Use when [trigger condition]. [What this skill helps with].
version: 1.0.0
license: MIT
---
```

## 3. Writing Principles (The "Claude Way")
When writing the body of `SKILL.md`, adhere to these best practices:

* **Conciseness**: Assume the agent is smart. Do not explain what a PDF or a Git repo is. Focus only on the unique logic of the skill.
* **Progressive Disclosure**: Keep `SKILL.md` under 500 lines. If more detail is needed, link to secondary files (e.g., `[See ADVANCED.md](ADVANCED.md)`) only one level deep.
* **Forward Slashes**: Always use `/` for paths, never `\`.
* **Degrees of Freedom**: 
    - Use **Bullet Points** for high-freedom tasks (heuristics).
    - Use **Code Blocks** for medium-freedom (templates).
    - Use **Specific Bash Commands** for low-freedom (fragile operations).

## 4. Workflow & Feedback Loops
For complex tasks, include:
1.  **Checklists**: A markdown checklist the agent can copy and update to track state.
2.  **Validation Loops**: A "Plan-Validate-Execute" pattern. (e.g., Run a script to check a config file BEFORE applying changes).
3.  **Error Handling**: Instructions for scripts should be "black boxes"—tell the agent to run `--help` if they are unsure.

## 5. Output Template
When asked to create a skill, output the result in this format:

### [Folder Name]
**Path:** `.agent/skills/[skill-name]/`

### [SKILL.md]
```markdown
---
name: [gerund-name]
description: [3rd-person description]
---

# [Skill Title]

## When to use this skill
- [Trigger 1]
- [Trigger 2]

## Workflow
[Insert checklist or step-by-step guide here]

## Instructions
[Specific logic, code snippets, or rules]

## Resources
- [Link to scripts/ or resources/]
[Supporting Files]
(If applicable, provide the content for scripts/ or examples/)

---

## Post-Creation Steps

After creating a skill in `.agent/skills/[skill-name]/`:

### 1. Verify Workspace Symlinks Exist

Check if multi-IDE symlinks are already set up:
```bash
ls -la .cursor/skills .claude/skills
```

If symlinks exist pointing to `.agent/skills`, you're done! The skill works in all IDEs immediately.

If not, set up workspace-level symlinks:
```bash
# Option 1: Run the setup script
./scripts/setup-multi-ide-skills.sh

# Option 2: Manual setup
mkdir -p .cursor .claude
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
```

### 2. Test the Skill

Verify the skill is discoverable:

**Google Antigravity:**
```
List available skills
/[skill-name]
```

**Claude Code:**
```
What skills are available?
/[skill-name]
```

**Cursor:**
```
/ [search for skill-name]
/[skill-name]
```

### 3. Validate Frontmatter

Ensure frontmatter parses correctly:
```bash
# Check YAML syntax
head -20 .agent/skills/[skill-name]/SKILL.md

# Verify required fields are present
grep -A 5 "^---$" .agent/skills/[skill-name]/SKILL.md | head -10
```

## Usage Examples

**Example 1: Simple utility skill**
```
/creating-skills

"Create a skill for validating JSON files that checks syntax,
validates against schemas, and suggests fixes for common errors"
```

**Example 2: Complex workflow skill**
```
/creating-skills

"Create a skill for API testing that generates test cases,
validates responses, checks error handling, and creates reports.
Include scripts for running tests and templates for test cases."
```

**Example 3: IDE-specific features**
```
/creating-skills

"Create a read-only research skill for analyzing codebases that
finds patterns, generates summaries, and creates documentation.
Should run in an isolated context with only read permissions."

# This would use Claude Code-specific frontmatter:
# context: fork
# agent: Explore
# allowed-tools: [Read, Grep, Glob]
```

## Troubleshooting

**Skill not appearing in IDE:**
1. Check skill exists: `ls .agent/skills/[skill-name]`
2. Verify SKILL.md exists: `ls .agent/skills/[skill-name]/SKILL.md`
3. Check frontmatter syntax (valid YAML between `---` markers)
4. Verify workspace symlinks: `ls -la .cursor/skills .claude/skills`
5. Restart IDE

**Frontmatter parse errors:**
- Ensure closing `---` is present
- Use spaces, not tabs for indentation
- Validate YAML syntax online or with linter

**Skill not auto-invoking:**
- Check `description` includes relevant keywords
- Ensure `disable-model-invocation` is not set to `true`
- Try manual invocation first: `/[skill-name]`

## Reference

See [docs/skill-frontmatter-template.md](../../../docs/skill-frontmatter-template.md) for complete frontmatter reference and examples.
