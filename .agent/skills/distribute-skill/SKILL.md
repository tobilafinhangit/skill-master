---
name: distribute-skill
description: Copies skills to another repository's .agent/skills directory and sets up multi-IDE compatibility. Use when installing, copying, or updating skills in a different project.
version: 2.0.0
license: MIT
---

# Distribute Skill

Simplifies the process of installing or copying skills from the current workspace to other repositories on your machine. Automatically sets up multi-IDE compatibility (Google Antigravity, Claude Code, Cursor) using workspace-level symlinks.

## When to Use This Skill
- The user says "Copy this skill to my other repo".
- You want to install a standard skill (like `troubleshooting`) into a new project.
- You are setting up a new repository and want to bootstrap it with essential skills.

## Prerequisite Checks

Before copying anything:
1. **Source**: Does the skill exist in `.agent/skills/[name]`?
2. **Target**: Does the target repository path exist?
3. **Destination**: Does `.agent/skills` exist in the target? If not, create it.
4. **Multi-IDE Setup**: Are workspace-level symlinks set up in target? If not, create them.

## Distribution Process

### 1. Identify Source and Target

**Ask the user if not provided:**
- **Source Skill(s)**: `[skill-name]` or `all` (e.g., `troubleshooting`, `planning`)
- **Target Repository**: `[absolute-path]` (e.g., `/Users/me/projects/my-app`)

### 2. Validation

```bash
# Verify source skill exists
ls .agent/skills/[skill-name]

# Verify target repository exists
ls [target-repo]
```

### 3. Copy Skill(s)

```bash
# Create destination directory
mkdir -p [target-repo]/.agent/skills

# Copy single skill
cp -r .agent/skills/[skill-name] [target-repo]/.agent/skills/

# OR copy multiple skills
cp -r .agent/skills/skill-1 .agent/skills/skill-2 [target-repo]/.agent/skills/

# OR copy all skills
cp -r .agent/skills/* [target-repo]/.agent/skills/
```

### 4. Set Up Multi-IDE Compatibility

**Check if workspace symlinks already exist:**
```bash
ls -la [target-repo]/.cursor/skills [target-repo]/.claude/skills
```

**If symlinks don't exist, create them (workspace-level):**
```bash
# Create IDE directories
mkdir -p [target-repo]/.cursor [target-repo]/.claude

# Create workspace-level symlinks (ONE symlink per IDE, not per skill!)
cd [target-repo]
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
```

**Important:** Use workspace-level symlinks (`.cursor/skills/` → `.agent/skills/`) instead of per-skill symlinks. This is simpler and makes all current and future skills work automatically.

### 5. Verification

```bash
# Verify skill was copied
ls -R [target-repo]/.agent/skills/[skill-name]

# Verify workspace symlinks exist (if created)
ls -la [target-repo]/.cursor/skills
ls -la [target-repo]/.claude/skills

# Should show:
# .cursor/skills -> .agent/skills
# .claude/skills -> .agent/skills

# Verify skill is accessible via symlinks
ls [target-repo]/.cursor/skills/[skill-name]
ls [target-repo]/.claude/skills/[skill-name]
```

## Complete Command Examples

### Example 1: Distribute Single Skill

```bash
TARGET="/Users/me/projects/my-api"
SKILL="troubleshooting"

# 1. Copy skill
mkdir -p "$TARGET/.agent/skills"
cp -r ".agent/skills/$SKILL" "$TARGET/.agent/skills/"

# 2. Set up multi-IDE (if not already done)
if [ ! -L "$TARGET/.cursor/skills" ]; then
    cd "$TARGET"
    mkdir -p .cursor .claude
    ln -s .agent/skills .cursor/skills
    ln -s .agent/skills .claude/skills
    cd -
fi

# 3. Verify
ls -R "$TARGET/.agent/skills/$SKILL"
ls -la "$TARGET/.cursor/skills" "$TARGET/.claude/skills"
```

### Example 2: Distribute Multiple Skills

```bash
TARGET="/Users/me/projects/my-api"
SKILLS="planning troubleshooting test-driven-development"

# 1. Copy skills
mkdir -p "$TARGET/.agent/skills"
for skill in $SKILLS; do
    cp -r ".agent/skills/$skill" "$TARGET/.agent/skills/"
done

# 2. Set up multi-IDE (once per repo)
cd "$TARGET"
mkdir -p .cursor .claude
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
cd -

# 3. Verify
ls "$TARGET/.agent/skills"
```

### Example 3: Distribute All Skills

```bash
TARGET="/Users/me/projects/new-project"

# 1. Copy all skills
mkdir -p "$TARGET/.agent/skills"
cp -r .agent/skills/* "$TARGET/.agent/skills/"

# 2. Set up multi-IDE
cd "$TARGET"
mkdir -p .cursor .claude
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
cd -

# 3. Verify
ls "$TARGET/.agent/skills"
ls -la "$TARGET/.cursor/skills" "$TARGET/.claude/skills"
```

### Example 4: Using Setup Script (Recommended)

```bash
TARGET="/Users/me/projects/my-api"
SKILL="troubleshooting"

# 1. Copy skill
mkdir -p "$TARGET/.agent/skills"
cp -r ".agent/skills/$SKILL" "$TARGET/.agent/skills/"

# 2. Copy and run setup script
cp scripts/setup-multi-ide-skills.sh "$TARGET/scripts/"
cd "$TARGET"
./scripts/setup-multi-ide-skills.sh
cd -
```

## Workflow Steps

### Step 1: Gather Information

Ask the user if not provided:
1. **Which skill(s)** to distribute? (name, list, or "all")
2. **Target repository path** (absolute path)

### Step 2: Validate

Before copying:
```bash
# Check source skill exists
ls .agent/skills/[skill-name] || echo "❌ Source skill not found"

# Check target repo exists
ls [target-repo] || echo "❌ Target repo not found"
```

### Step 3: Copy Skill(s)

```bash
# Create directory
mkdir -p [target-repo]/.agent/skills

# Copy (choose one)
cp -r .agent/skills/[skill-name] [target-repo]/.agent/skills/        # Single
cp -r .agent/skills/{skill1,skill2} [target-repo]/.agent/skills/     # Multiple
cp -r .agent/skills/* [target-repo]/.agent/skills/                   # All
```

### Step 4: Set Up Multi-IDE Support

Check if symlinks already exist:
```bash
ls -la [target-repo]/.cursor/skills [target-repo]/.claude/skills
```

If they don't exist, create workspace-level symlinks:
```bash
cd [target-repo]
mkdir -p .cursor .claude
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
```

### Step 5: Verify Installation

```bash
# Confirm skill exists in target
ls [target-repo]/.agent/skills/[skill-name]

# Confirm symlinks point correctly
readlink [target-repo]/.cursor/skills    # Should show: .agent/skills
readlink [target-repo]/.claude/skills    # Should show: .agent/skills

# Test skill is accessible
ls [target-repo]/.cursor/skills/[skill-name]
ls [target-repo]/.claude/skills/[skill-name]
```

### Step 6: Report Success

Inform the user:
```
✅ Distributed [skill-name] to [target-repo]

The skill is now available in:
- Google Antigravity (.agent/skills/)
- Claude Code (.claude/skills/ → .agent/skills/)
- Cursor (.cursor/skills/ → .agent/skills/)

Test it in the target repo:
cd [target-repo]
/[skill-name]
```

## Important Notes

### Overwrite Handling

If the skill already exists at the destination:
1. Ask before overwriting (unless user said "update" or "force")
2. Consider backing up first: `cp -r [target]/.agent/skills/[name] [target]/.agent/skills/[name].backup`
3. Show a diff if the skill changed: `diff -r .agent/skills/[name] [target]/.agent/skills/[name]`

### Workspace vs Per-Skill Symlinks

**Old approach (deprecated):**
```bash
# ❌ Per-skill symlinks (creates N symlinks for N skills)
ln -s ../../.agent/skills/skill-1 .cursor/skills/skill-1
ln -s ../../.agent/skills/skill-2 .cursor/skills/skill-2
```

**New approach (recommended):**
```bash
# ✅ Workspace-level symlinks (one symlink per IDE)
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
```

Benefits of workspace-level symlinks:
- Simpler setup (one symlink per IDE, not per skill)
- All current and future skills work automatically
- Easier to maintain
- Matches the multi-IDE setup in this repo

### Batch Distribution

When copying all skills:
```bash
# Option 1: Copy everything
cp -r .agent/skills/* [target]/.agent/skills/

# Option 2: Copy specific category (if skills are organized)
cp -r .agent/skills/{planning,troubleshooting,debugging}* [target]/.agent/skills/

# Option 3: Exclude certain skills
rsync -av --exclude='internal-*' .agent/skills/ [target]/.agent/skills/
```

**Warning:** Be careful about overwriting local customizations in the target repo!

## Troubleshooting

### Symlinks Not Working

**Issue:** Symlinks don't work on Windows without admin rights.

**Solution:** Use directory junctions:
```cmd
mklink /J .cursor\skills .agent\skills
mklink /J .claude\skills .agent\skills
```

Or hard copy (requires manual sync):
```bash
cp -r .agent/skills .cursor/skills
cp -r .agent/skills .claude/skills
```

### Permission Errors

**Issue:** Permission denied when copying to target.

**Solution:**
```bash
# Check permissions
ls -la [target-repo]

# Fix ownership (if needed)
sudo chown -R $USER [target-repo]/.agent

# Or copy with sudo (last resort)
sudo cp -r .agent/skills/[name] [target]/.agent/skills/
```

### Skill Not Appearing in Target IDE

**Checklist:**
1. Skill exists in target: `ls [target]/.agent/skills/[name]`
2. Workspace symlinks exist: `ls -la [target]/.cursor/skills [target]/.claude/skills`
3. Symlinks point to correct target: `readlink [target]/.cursor/skills`
4. SKILL.md has valid frontmatter
5. Restart IDE in target repo

## Complete Workflow Examples

### Example 1: Distribute Single Skill

**User request:**
```
"Copy the planning skill to /Users/me/projects/api-server"
```

**Agent response:**
```bash
# Step 1: Validate source
ls .agent/skills/planning
# ✅ Found: .agent/skills/planning/SKILL.md

# Step 2: Validate target
ls /Users/me/projects/api-server
# ✅ Target repository exists

# Step 3: Copy skill
mkdir -p /Users/me/projects/api-server/.agent/skills
cp -r .agent/skills/planning /Users/me/projects/api-server/.agent/skills/

# Step 4: Check if multi-IDE symlinks exist
ls -la /Users/me/projects/api-server/.cursor/skills 2>/dev/null
# ❌ Not found - need to create

# Step 5: Set up multi-IDE compatibility
cd /Users/me/projects/api-server
mkdir -p .cursor .claude
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
cd -

# Step 6: Verify
ls /Users/me/projects/api-server/.agent/skills/planning
# ✅ SKILL.md found

readlink /Users/me/projects/api-server/.cursor/skills
# ✅ .agent/skills

readlink /Users/me/projects/api-server/.claude/skills
# ✅ .agent/skills
```

**Success message:**
```
✅ Successfully distributed 'planning' skill to /Users/me/projects/api-server

The skill is now available in all IDEs:
- Google Antigravity: .agent/skills/planning/
- Claude Code: .claude/skills/planning/ (via symlink)
- Cursor: .cursor/skills/planning/ (via symlink)

Test it:
cd /Users/me/projects/api-server
/planning
```

### Example 2: Distribute Multiple Skills

**User request:**
```
"Install planning, troubleshooting, and test-driven-development skills
in /Users/me/projects/my-app"
```

**Agent response:**
```bash
TARGET="/Users/me/projects/my-app"
SKILLS="planning troubleshooting test-driven-development"

# Validate source skills
for skill in $SKILLS; do
    ls .agent/skills/$skill || echo "❌ $skill not found"
done
# ✅ All skills found

# Copy skills
mkdir -p "$TARGET/.agent/skills"
for skill in $SKILLS; do
    echo "Copying $skill..."
    cp -r ".agent/skills/$skill" "$TARGET/.agent/skills/"
done

# Set up multi-IDE (once)
cd "$TARGET"
mkdir -p .cursor .claude
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
cd -

# Verify
echo "Installed skills:"
ls "$TARGET/.agent/skills"
# planning
# troubleshooting
# test-driven-development

echo "Multi-IDE symlinks:"
ls -la "$TARGET/.cursor/skills" "$TARGET/.claude/skills"
# .cursor/skills -> .agent/skills
# .claude/skills -> .agent/skills
```

**Success message:**
```
✅ Successfully distributed 3 skills to /Users/me/projects/my-app:
  - planning
  - troubleshooting
  - test-driven-development

All skills are available in Google Antigravity, Claude Code, and Cursor.
```

### Example 3: Update Existing Skill

**User request:**
```
"Update the troubleshooting skill in /Users/me/projects/api-server"
```

**Agent response:**
```bash
TARGET="/Users/me/projects/api-server"
SKILL="troubleshooting"

# Check if skill exists in target
if [ -d "$TARGET/.agent/skills/$SKILL" ]; then
    echo "⚠️  Skill already exists. Creating backup..."
    cp -r "$TARGET/.agent/skills/$SKILL" "$TARGET/.agent/skills/$SKILL.backup"
fi

# Update skill
cp -r ".agent/skills/$SKILL" "$TARGET/.agent/skills/"

echo "✅ Updated $SKILL skill"
echo "Backup saved at: $TARGET/.agent/skills/$SKILL.backup"
```

### Example 4: Bootstrap New Repository

**User request:**
```
"Set up essential skills in my new project at /Users/me/projects/new-api"
```

**Agent response:**
```bash
TARGET="/Users/me/projects/new-api"

# Copy essential skills
mkdir -p "$TARGET/.agent/skills"
echo "Installing essential skills..."

ESSENTIAL="planning troubleshooting test-driven-development"
for skill in $ESSENTIAL; do
    cp -r ".agent/skills/$skill" "$TARGET/.agent/skills/"
    echo "  ✅ $skill"
done

# Set up multi-IDE support
cd "$TARGET"
mkdir -p .cursor .claude
ln -s .agent/skills .cursor/skills
ln -s .agent/skills .claude/skills
cd -

# Copy setup script for future use
mkdir -p "$TARGET/scripts"
cp scripts/setup-multi-ide-skills.sh "$TARGET/scripts/"

echo "
✅ Bootstrap complete!

Installed skills:
$(ls "$TARGET/.agent/skills")

Multi-IDE support enabled for:
- Google Antigravity (.agent/skills/)
- Claude Code (.claude/skills/)
- Cursor (.cursor/skills/)

To add more skills later, run:
cd $TARGET
/distribute-skill
"
```

## Quick Reference

### Single Skill
```bash
cp -r .agent/skills/[name] [target]/.agent/skills/
cd [target] && ln -s .agent/skills .cursor/skills && ln -s .agent/skills .claude/skills
```

### Multiple Skills
```bash
cp -r .agent/skills/{skill1,skill2,skill3} [target]/.agent/skills/
cd [target] && ln -s .agent/skills .cursor/skills && ln -s .agent/skills .claude/skills
```

### All Skills
```bash
cp -r .agent/skills/* [target]/.agent/skills/
cd [target] && ln -s .agent/skills .cursor/skills && ln -s .agent/skills .claude/skills
```

## Related Documentation

- [Creating Skills](../creating-skills/SKILL.md) - How to create new skills
- [Multi-IDE Setup](../../../docs/installation-multi-ide.md) - Complete IDE setup guide
- [Frontmatter Template](../../../docs/skill-frontmatter-template.md) - Skill format reference
