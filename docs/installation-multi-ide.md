# Multi-IDE Installation Guide

This guide shows how to set up skills for use across Google Antigravity, Claude Code, and Cursor.

## Overview

The skill-master repository uses `.agent/skills/` as the primary location for skills (Google Antigravity's standard) and provides symlinks for other IDEs.

**Directory structure:**
```
.agent/skills/      # Primary (Google Antigravity native)
.cursor/skills/     # Symlink → .agent/skills/ (Cursor)
.claude/skills/     # Symlink → .agent/skills/ (Claude Code)
```

This approach ensures:
- ✅ Single source of truth (one skill directory to maintain)
- ✅ Compatibility with all three major AI IDEs
- ✅ No duplication of skills
- ✅ Easy updates (edit once, works everywhere)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/skill-master.git
cd skill-master
```

### 2. Create Symlinks

Run the setup script to create symlinks for Cursor and Claude Code:

```bash
./scripts/setup-multi-ide-skills.sh
```

This creates:
- `.cursor/skills/` → `.agent/skills/`
- `.claude/skills/` → `.agent/skills/`

### 3. IDE-Specific Setup

Follow the IDE-specific instructions below based on which AI IDE you're using.

---

## Google Antigravity Setup

Google Antigravity uses `.agent/skills/` natively, so no additional setup is needed!

### Installation

1. **Workspace skills (project-specific)**:
   - Skills in `.agent/skills/` are automatically discovered ✅
   - No configuration needed

2. **Global skills (user-wide)**:
   ```bash
   # Option 1: Symlink the entire skills directory
   ln -s "$(pwd)/.agent/skills" ~/.gemini/antigravity/skills/skill-master

   # Option 2: Symlink individual skills
   ln -s "$(pwd)/.agent/skills/planning" ~/.gemini/antigravity/skills/planning
   ln -s "$(pwd)/.agent/skills/skill-strategist" ~/.gemini/antigravity/skills/skill-strategist
   ```

### Verification

In Google Antigravity:
```
List available skills
/planning
```

You should see all skills from `.agent/skills/` directory.

### Resources
- [Getting Started with Google Antigravity Skills](https://codelabs.developers.google.com/getting-started-with-antigravity-skills)
- [Google Antigravity Documentation](https://antigravity.google/docs/skills)

---

## Claude Code Setup

Claude Code uses `.claude/skills/` which we've symlinked to `.agent/skills/`.

### Installation

1. **Workspace skills (project-specific)**:
   - Skills in `.claude/skills/` (symlink) are automatically discovered ✅
   - Verify symlink exists:
     ```bash
     ls -la .claude/skills
     # Should show: .claude/skills -> ../.agent/skills
     ```

2. **Global skills (user-wide)**:
   ```bash
   # Option 1: Symlink the entire skills directory
   ln -s "$(pwd)/.agent/skills" ~/.claude/skills/skill-master

   # Option 2: Symlink individual skills
   ln -s "$(pwd)/.agent/skills/planning" ~/.claude/skills/planning
   ln -s "$(pwd)/.agent/skills/skill-strategist" ~/.claude/skills/skill-strategist
   ```

3. **Plugin installation** (for superpowers):
   ```
   /plugin marketplace add obra/superpowers-marketplace
   ```

### Verification

In Claude Code:
```
What skills are available?
/planning
```

You should see all skills from `.claude/skills/` (which links to `.agent/skills/`).

### Advanced Features

Claude Code supports advanced skill features via frontmatter:

```yaml
---
name: my-skill
description: Use when...
allowed-tools: [Read, Grep, Glob]  # Tool restrictions
context: fork  # Run in subagent
agent: Explore  # Subagent type
---
```

See [skill-frontmatter-template.md](skill-frontmatter-template.md) for details.

### Resources
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Agent Skills Open Standard](https://agentskills.io)

---

## Cursor Setup

Cursor uses `.cursor/skills/` which we've symlinked to `.agent/skills/`.

### Installation

1. **Workspace skills (project-specific)**:
   - Skills in `.cursor/skills/` (symlink) are automatically discovered ✅
   - Verify symlink exists:
     ```bash
     ls -la .cursor/skills
     # Should show: .cursor/skills -> ../.agent/skills
     ```

2. **Global skills (user-wide)**:
   ```bash
   # Option 1: Symlink the entire skills directory
   ln -s "$(pwd)/.agent/skills" ~/.cursor/skills/skill-master

   # Option 2: Symlink individual skills
   ln -s "$(pwd)/.agent/skills/planning" ~/.cursor/skills/planning
   ln -s "$(pwd)/.agent/skills/skill-strategist" ~/.cursor/skills/planning
   ```

3. **GitHub installation**:
   - Open Cursor Settings (Cmd+Shift+J / Ctrl+Shift+J)
   - Navigate to Rules
   - Click "Add Rule" → "Remote Rule (Github)"
   - Enter repository URL: `https://github.com/your-org/skill-master`

### Verification

In Cursor:
```
/ [search for skills]
/planning
```

You should see all skills from `.cursor/skills/` (which links to `.agent/skills/`).

### Cursor-Specific Features

Cursor supports these frontmatter fields:

```yaml
---
name: my-skill
description: Use when...
compatibility:
  min-version: "1.0.0"  # Min Cursor version
disable-model-invocation: true  # Manual invoke only
---
```

See [skill-frontmatter-template.md](skill-frontmatter-template.md) for details.

### Migration from Commands

Cursor 2.4+ includes `/migrate-to-skills` to convert slash commands to skills:

```
/migrate-to-skills
```

### Resources
- Cursor Skills Documentation (see user-provided docs)

---

## Troubleshooting

### Symlinks Not Working

**Issue**: Symlinks don't work on your system (e.g., Windows without admin rights).

**Solution**: Use directory junctions (Windows) or hard copy:

```bash
# Windows: Use junction instead of symlink
mklink /J .cursor\skills .agent\skills
mklink /J .claude\skills .agent\skills

# All platforms: Hard copy (requires manual sync)
cp -r .agent/skills .cursor/skills
cp -r .agent/skills .claude/skills
```

### Skills Not Discovered

**Issue**: IDE doesn't discover skills after symlink creation.

**Checklist**:
1. Verify symlink exists: `ls -la .cursor/skills .claude/skills`
2. Check symlink target is correct: `readlink .cursor/skills`
3. Restart IDE
4. Check IDE skill directories in settings
5. Verify SKILL.md files have valid frontmatter

### Duplicate Skills

**Issue**: Skills appear twice in the skill list.

**Cause**: Both `.agent/skills/` and symlinked directory (`.cursor/skills/` or `.claude/skills/`) are being scanned.

**Solution**: The IDE should deduplicate by resolving symlinks. If not, configure IDE to only scan one directory:
- For Claude Code: Set skill directory preference
- For Cursor: Configure in Settings → Rules
- For Google Antigravity: Only `.agent/skills/` is scanned by default

### Frontmatter Parse Errors

**Issue**: IDE shows errors when loading skills.

**Solution**: Validate frontmatter syntax:
```bash
# Check for common issues
grep -A 5 "^---$" .agent/skills/*/SKILL.md | head -50
```

Common problems:
- Missing closing `---`
- Invalid YAML syntax (tabs instead of spaces, incorrect indentation)
- Unsupported field names (typos)

Use the [frontmatter template](skill-frontmatter-template.md) as reference.

### Skill Not Auto-Invoking

**Issue**: Skill doesn't activate when you expect it to.

**Checklist**:
1. Check `description` field includes relevant keywords
2. Ensure `disable-model-invocation` is not set to `true` (or is absent)
3. Try invoking manually to verify skill works: `/skill-name`
4. Rephrase your request to match description keywords more closely

---

## Platform Comparison

| Feature | Google Antigravity | Claude Code | Cursor |
|---------|-------------------|-------------|--------|
| **Directory** | `.agent/skills/` | `.claude/skills/` | `.cursor/skills/` |
| **Global dir** | `~/.gemini/antigravity/skills/` | `~/.claude/skills/` | `~/.cursor/skills/` |
| **Auto-discovery** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Manual invoke** | ✅ `/skill-name` | ✅ `/skill-name` | ✅ `/skill-name` |
| **Symlink support** | ✅ Yes | ✅ Yes | ✅ Yes |
| **GitHub install** | ✅ Yes | ✅ Via plugins | ✅ Via rules |
| **Advanced frontmatter** | Basic | ✅ Full support | Partial |
| **Subagent forking** | ❌ No | ✅ Yes (`context: fork`) | ❌ No |
| **Tool restrictions** | ❌ No | ✅ Yes (`allowed-tools`) | ❌ No |
| **Version constraints** | ❌ No | ❌ No | ✅ Yes (`compatibility`) |

---

## Best Practices

### 1. Use .agent/skills/ as Primary

Keep `.agent/skills/` as your primary skills directory. This:
- Works natively with Google Antigravity
- Supports other IDEs via symlinks
- Maintains single source of truth

### 2. Test Across IDEs

Before publishing skills:
1. Test in Google Antigravity (native)
2. Test in Claude Code (via symlink)
3. Test in Cursor (via symlink)
4. Verify skill appears in skill list
5. Test both auto-invocation and manual invocation

### 3. Use Compatible Frontmatter

Stick to the basic + recommended frontmatter template for maximum compatibility:

```yaml
---
name: skill-name
description: Use when [condition].
version: 1.0.0
license: MIT
---
```

Only add IDE-specific fields when necessary.

### 4. Document IDE-Specific Features

If using IDE-specific frontmatter (e.g., Claude Code's `allowed-tools`), document this in the skill's README:

```markdown
## IDE Compatibility

This skill uses Claude Code-specific features:
- `allowed-tools`: Restricts to read-only tools
- `context: fork`: Runs in isolated subagent

For other IDEs, the skill works but without these restrictions.
```

### 5. Version Your Skills

Use semantic versioning in frontmatter:
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

This helps users understand compatibility and update impact.

---

## Updating Skills

### Single Edit, Multi-IDE Update

Since all IDEs use the same underlying `.agent/skills/` directory (via symlinks), editing a skill once updates it everywhere:

```bash
# Edit skill
vim .agent/skills/planning/SKILL.md

# Changes immediately available in:
# - Google Antigravity (.agent/skills/)
# - Claude Code (.claude/skills/ → .agent/skills/)
# - Cursor (.cursor/skills/ → .agent/skills/)
```

No need to sync or duplicate edits!

### Version Bumping

When updating a skill:
1. Make your changes to SKILL.md
2. Update `version` in frontmatter
3. Test in all target IDEs
4. Commit changes

```bash
# Update skill
vim .agent/skills/planning/SKILL.md

# Bump version: 1.0.0 → 1.1.0
# Commit
git add .agent/skills/planning/SKILL.md
git commit -m "feat(planning): Add new planning templates (v1.1.0)"
```

---

## FAQ

### Q: Can I use different skills in different IDEs?

**A**: Yes! You can:
1. Use `.agent/skills/` for shared skills (works everywhere)
2. Add IDE-specific skills to respective directories:
   - `.cursor/skills/cursor-only-skill/` (Cursor only)
   - `.claude/skills/claude-only-skill/` (Claude Code only)

Just don't create these inside the symlinked directory.

### Q: What if I want to use .claude/skills/ as primary instead?

**A**: You can! Just reverse the symlinks:
```bash
# Use .claude/skills/ as primary
rm .cursor/skills .agent/skills  # Remove old symlinks
ln -s .claude/skills .cursor/skills
ln -s .claude/skills .agent/skills
```

However, `.agent/skills/` is recommended for Google Antigravity compatibility.

### Q: How do I share skills with my team?

**A**: Three options:

1. **Git repository** (recommended):
   ```bash
   git clone https://github.com/your-org/skill-master.git
   cd skill-master
   ./scripts/setup-multi-ide-skills.sh
   ```

2. **Plugin system** (Claude Code):
   ```
   /plugin marketplace add your-org/skill-master
   ```

3. **GitHub rules** (Cursor):
   - Settings → Rules → Add Rule → Remote Rule (Github)
   - Enter repo URL

### Q: Can I use this with other AI tools?

**A**: Yes! The [Agent Skills open standard](https://agentskills.io) is designed for portability. As long as the tool supports:
- SKILL.md format
- YAML frontmatter
- Directory-based discovery

...your skills should work.

---

## Next Steps

- ✅ Set up symlinks for your IDE
- ✅ Verify skills are discovered
- ✅ Test skill invocation (manual and auto)
- ✅ Explore [frontmatter options](skill-frontmatter-template.md)
- ✅ Create your first custom skill
- ✅ Share skills with your team

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/skill-master/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/skill-master/discussions)
- **Documentation**: [docs/](.)
