# Skill Frontmatter Template

This template shows the recommended YAML frontmatter for skills that work across multiple IDEs (Google Antigravity, Claude Code, and Cursor).

## Basic Template (Minimum Required)

```yaml
---
name: skill-name
description: Use when [triggering condition]. [What this skill helps with].
---
```

**Required fields:**
- `name`: Lowercase kebab-case identifier (letters, numbers, hyphens only)
- `description`: Third-person description focusing on WHEN to use, not HOW it works

## Recommended Template (With Versioning)

```yaml
---
name: skill-name
description: Use when [triggering condition]. [What this skill helps with].
version: 1.0.0
license: MIT
---
```

**Recommended fields:**
- `version`: Semantic versioning (MAJOR.MINOR.PATCH)
- `license`: License identifier (e.g., MIT, Apache-2.0)

## Full Template (With All Optional Fields)

```yaml
---
name: skill-name
description: Use when [triggering condition]. [What this skill helps with].
version: 1.0.0
license: MIT

# Optional metadata
metadata:
  author: Your Name
  category: development
  tags: [planning, debugging, testing]
  created: 2026-01-24
  updated: 2026-01-24

# Cursor-specific (optional)
compatibility:
  min-version: "1.0.0"
  max-version: "2.0.0"
disable-model-invocation: false  # Set true to prevent auto-invocation

# Claude Code-specific (optional)
allowed-tools: [Read, Write, Bash, Grep]  # Tool restrictions
agent: general-purpose  # Subagent type for context: fork
context: fork  # Run in isolated subagent
argument-hint: "[filename] [format]"  # Autocomplete hint
user-invocable: true  # Show in / menu

# Hooks (optional - Claude Code)
hooks:
  before: |
    # Shell command to run before skill execution
  after: |
    # Shell command to run after skill execution
---
```

## Field Descriptions

### Required Fields

#### `name`
- **Format**: Lowercase kebab-case (e.g., `my-skill-name`)
- **Allowed characters**: Letters, numbers, hyphens
- **Max length**: 64 characters
- **Example**: `test-driven-development`, `api-design`, `systematic-debugging`

#### `description`
- **Purpose**: Tells Claude WHEN to use this skill
- **Format**: Third person, start with "Use when..."
- **Max length**: 500 characters (recommended)
- **Focus**: Triggering conditions, NOT the process
- **Examples**:
  - ✅ "Use when writing tests, implementing TDD, or ensuring code coverage"
  - ❌ "This skill teaches you how to write tests step by step"

### Recommended Fields

#### `version`
- **Format**: Semantic versioning (MAJOR.MINOR.PATCH)
- **Example**: `1.0.0`, `2.1.3`
- **Helps with**: Compatibility tracking, update notifications

#### `license`
- **Common values**: `MIT`, `Apache-2.0`, `GPL-3.0`, `BSD-3-Clause`
- **Example**: `MIT`

### Optional Metadata Fields

#### `metadata`
- **Purpose**: Additional context about the skill
- **Sub-fields**:
  - `author`: Creator name
  - `category`: Skill category (development, deployment, documentation, etc.)
  - `tags`: Array of searchable keywords
  - `created`: Creation date (ISO format)
  - `updated`: Last update date (ISO format)

### Cursor-Specific Fields

#### `compatibility`
- **Purpose**: Version constraints for Cursor
- **Sub-fields**:
  - `min-version`: Minimum Cursor version required
  - `max-version`: Maximum Cursor version supported

#### `disable-model-invocation`
- **Type**: Boolean (true/false)
- **Default**: false
- **When to use**: Set to `true` for skills you want to invoke manually only
- **Example use cases**: Deployment scripts, commit workflows, destructive operations

### Claude Code-Specific Fields

#### `allowed-tools`
- **Type**: Array of tool names
- **Purpose**: Restrict which tools Claude can use when this skill is active
- **Example**: `[Read, Grep, Glob]` for read-only mode
- **Common tools**: Read, Write, Edit, Bash, Grep, Glob, Task

#### `agent`
- **Type**: String
- **Purpose**: Specify which subagent type to use with `context: fork`
- **Options**: `Explore`, `Plan`, `general-purpose`, `Bash`
- **Example**: `Explore` for read-only research tasks

#### `context`
- **Type**: String
- **Value**: `fork` (to run in isolated subagent)
- **Purpose**: Execute skill in a separate context without conversation history
- **When to use**: Research tasks, isolated operations

#### `argument-hint`
- **Type**: String
- **Purpose**: Show autocomplete hint for expected arguments
- **Examples**: `[issue-number]`, `[filename] [format]`, `[environment]`

#### `user-invocable`
- **Type**: Boolean
- **Default**: true
- **Purpose**: Control whether skill appears in `/` menu
- **When to set false**: Background knowledge skills that shouldn't be manually invoked

#### `hooks`
- **Type**: Object with `before` and `after` fields
- **Purpose**: Run shell commands before/after skill execution
- **Example**:
  ```yaml
  hooks:
    before: |
      echo "Starting skill execution..."
      git status
    after: |
      echo "Skill execution complete"
  ```

## IDE Compatibility Matrix

| Field | Google Antigravity | Claude Code | Cursor | Notes |
|-------|-------------------|-------------|--------|-------|
| `name` | ✅ Required | ✅ Optional* | ✅ Required | *Uses dir name if omitted |
| `description` | ✅ Required | ✅ Recommended | ✅ Required | Critical for auto-invocation |
| `version` | ✅ Supported | ✅ Supported | ✅ Supported | Semantic versioning |
| `license` | ✅ Supported | ✅ Supported | ✅ Supported | License identifier |
| `metadata` | ✅ Supported | ✅ Supported | ✅ Supported | Arbitrary key-value pairs |
| `compatibility` | ❌ Ignored | ❌ Ignored | ✅ Supported | Cursor version constraints |
| `disable-model-invocation` | ❌ Ignored | ⚠️ Similar* | ✅ Supported | *Claude Code has separate field |
| `allowed-tools` | ❌ Ignored | ✅ Supported | ❌ Ignored | Claude Code tool restrictions |
| `agent` | ❌ Ignored | ✅ Supported | ❌ Ignored | Claude Code subagent selection |
| `context` | ❌ Ignored | ✅ Supported | ❌ Ignored | Claude Code forking |
| `argument-hint` | ❌ Ignored | ✅ Supported | ❌ Ignored | Claude Code autocomplete |
| `user-invocable` | ❌ Ignored | ✅ Supported | ❌ Ignored | Claude Code menu visibility |
| `hooks` | ❌ Ignored | ✅ Supported | ❌ Ignored | Claude Code lifecycle hooks |

**Legend:**
- ✅ Supported: Field is recognized and used
- ❌ Ignored: Field is safely ignored (forward-compatible)
- ⚠️ Similar: Different field name but similar functionality

## Best Practices

### 1. Start Simple
Begin with the basic template (name + description) and add fields as needed.

### 2. Write Great Descriptions
The description is the MOST IMPORTANT field for skill discovery:
- Start with "Use when..."
- Include triggering conditions, symptoms, error messages
- Include synonyms and related terms
- Focus on WHEN, not HOW
- Keep it under 500 characters

### 3. Use Versioning
Track changes with semantic versioning:
- MAJOR: Breaking changes
- MINOR: New features, backward-compatible
- PATCH: Bug fixes, small improvements

### 4. Add Metadata for Organization
Use `category` and `tags` to organize large skill libraries:
- Categories: development, deployment, documentation, debugging, testing, etc.
- Tags: Specific technologies, frameworks, or concepts

### 5. Test Across IDEs
Before publishing:
1. Test in Google Antigravity (if using .agent/skills/)
2. Test in Claude Code (if using .claude/skills/)
3. Test in Cursor (if using .cursor/skills/)
4. Verify frontmatter parses without errors in all IDEs

### 6. Keep It Compatible
Only use IDE-specific fields when necessary. Stick to the basic + recommended template for maximum portability.

## Examples from Real Skills

### Example 1: Simple Skill (TDD)
```yaml
---
name: test-driven-development
description: Use when writing tests, implementing TDD methodology, or ensuring test coverage for new features.
version: 1.0.0
license: MIT
---
```

### Example 2: Manual-Only Skill (Deploy)
```yaml
---
name: deploy
description: Deploy the application to production or staging environments.
version: 1.0.0
license: MIT
disable-model-invocation: true  # Only invoke manually
argument-hint: "[environment]"
---
```

### Example 3: Research Skill with Forking
```yaml
---
name: deep-research
description: Research a topic thoroughly by reading code, analyzing patterns, and summarizing findings.
version: 1.0.0
license: MIT
context: fork  # Run in isolated context
agent: Explore  # Use read-only Explore agent
allowed-tools: [Read, Grep, Glob]  # Read-only tools
---
```

### Example 4: Rich Metadata Skill
```yaml
---
name: api-design-principles
description: Use when designing APIs, creating endpoints, or reviewing API structure and conventions.
version: 2.1.0
license: MIT
metadata:
  author: Superpowers Team
  category: development
  tags: [api, rest, graphql, design, architecture]
  created: 2024-06-15
  updated: 2026-01-24
---
```

## Migration Guide

### Upgrading Existing Skills

If you have skills with minimal frontmatter, add recommended fields:

```yaml
# Before (minimal)
---
name: my-skill
description: Use when doing X.
---

# After (recommended)
---
name: my-skill
description: Use when doing X.
version: 1.0.0
license: MIT
metadata:
  category: development
  tags: [relevant, keywords]
---
```

### Adding IDE-Specific Features

Only add IDE-specific fields when needed:

```yaml
# For manual-only invoke (Cursor):
disable-model-invocation: true

# For tool restrictions (Claude Code):
allowed-tools: [Read, Grep, Glob]

# For subagent execution (Claude Code):
context: fork
agent: Explore
```

## Validation

Use this checklist to validate your skill frontmatter:

- [ ] `name` uses only lowercase letters, numbers, and hyphens
- [ ] `name` is 64 characters or less
- [ ] `description` starts with "Use when..." (recommended)
- [ ] `description` is 500 characters or less
- [ ] `version` follows semantic versioning (if present)
- [ ] `license` is a valid SPDX identifier (if present)
- [ ] IDE-specific fields are only used when necessary
- [ ] Frontmatter parses without errors in target IDEs
- [ ] Skill is discoverable via description keywords

## Resources

- [Agent Skills Open Standard](https://agentskills.io)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Cursor Skills Documentation](https://docs.cursor.com/skills) (from user-provided docs)
- Google Antigravity Skills: [Google Codelabs](https://codelabs.developers.google.com/getting-started-with-antigravity-skills)
