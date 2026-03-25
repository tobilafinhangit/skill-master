---
name: distribute-skill
description: Single entry point for all skill distribution — sync local edits back to skill-master and propagate to all repos, pull latest from skill-master, or copy skills to new repos. Use when the user edits a skill locally, says "sync skills", "update skill-master", "pull skills", or "distribute skill".
version: 3.0.0
license: MIT
---

# Distribute Skill

The single command for moving skills between repos and skill-master. Detects what you need based on context and arguments.

## Modes

| Mode | Trigger | What it does |
|------|---------|--------------|
| **sync** | `/distribute-skill sync [skill-name]` or "sync this to skill-master" | Push local edits → skill-master → all repos |
| **pull** | `/distribute-skill pull` or "pull latest skills" | Update submodule from skill-master in current repo |
| **propagate** | `/distribute-skill propagate` or "update all repos" | Update submodule in ALL consuming repos |
| **copy** | `/distribute-skill copy [skill] [target-path]` | Copy a skill to a repo without submodule |
| **auto** | `/distribute-skill` (no args) | Detect dirty skills and suggest the right mode |

If no mode is specified, run **auto-detect** (see below).

## Auto-Detect Mode

When invoked with no arguments:

1. Check if any skill files in the current repo differ from the submodule:
   ```bash
   # Compare local skills against submodule source
   for skill_dir in .claude/skills/*/SKILL.md .agent/skills/*/SKILL.md; do
     skill_name=$(basename $(dirname "$skill_dir"))
     submodule_path="submodules/skill-master/.agent/skills/$skill_name/SKILL.md"
     if [ -f "$submodule_path" ]; then
       if ! diff -q "$skill_dir" "$submodule_path" > /dev/null 2>&1; then
         echo "DIRTY: $skill_name"
       fi
     fi
   done
   ```

2. If dirty skills found → suggest **sync** mode
3. If no dirty skills → suggest **pull** mode (check if submodule is behind remote)
4. Show the suggestion and ask user to confirm before proceeding

## Skill-Master Location

- **Source repo**: `/Users/USER/code/repos/skill-master`
- **Remote**: `github.com:tobilafinhangit/skill-master.git`
- **Skill path within**: `.agent/skills/[skill-name]/SKILL.md`

## Consuming Repos

These repos have `submodules/skill-master` as a git submodule:

| Repo | Path |
|------|------|
| vetted-congrats-Flow-GENEROUS | `/Users/USER/code/repos/vetted-congrats-Flow-GENEROUS` |
| backend-restructing | `/Users/USER/code/repos/backend-restructing` |
| vettedai-audition-supabase-version | `/Users/USER/code/repos/vettedai-audition-supabase-version` |
| vfacoffeechat | `/Users/USER/code/repos/vfacoffeechat` |
| nts-opportunity-hour-digest | `/Users/USER/code/repos/nts-opportunity-hour-digest` |

When a new repo is added to the ecosystem, add it to this table.

---

## Mode: sync

Push a locally-edited skill back to skill-master and propagate to all repos.

### When to use
- You edited a skill in `.claude/skills/` or `.agent/skills/` in any repo
- User says "sync this to skill-master", "update skill-master", "push this skill"

### Workflow

#### Step 1: Identify the changed skill(s)

If a skill name is provided, use it. Otherwise, auto-detect:

```bash
# Find skills that differ from submodule
for skill_dir in .claude/skills/*/SKILL.md .agent/skills/*/SKILL.md; do
  [ -f "$skill_dir" ] || continue
  skill_name=$(basename $(dirname "$skill_dir"))
  submodule="submodules/skill-master/.agent/skills/$skill_name/SKILL.md"
  [ -f "$submodule" ] && ! diff -q "$skill_dir" "$submodule" > /dev/null 2>&1 && echo "$skill_name: $skill_dir"
done
```

Show the diff summary to the user and confirm before proceeding.

#### Step 2: Copy to skill-master

```bash
SKILL_MASTER="/Users/USER/code/repos/skill-master"

# For each dirty skill, copy the local version to skill-master
cp "$LOCAL_SKILL_PATH" "$SKILL_MASTER/.agent/skills/$SKILL_NAME/SKILL.md"
```

If the skill has additional files (not just SKILL.md), copy the entire directory.

#### Step 3: Commit and push skill-master

```bash
cd "$SKILL_MASTER"
git add ".agent/skills/$SKILL_NAME/"
git commit -m "feat($SKILL_NAME): [describe the change]

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"

# Pull remote first to avoid rejection
git stash  # if needed for unrelated dirty files
git pull --rebase
git stash pop  # if stashed
git push
```

#### Step 4: Propagate to all consuming repos

```bash
REPOS=(
  "/Users/USER/code/repos/vetted-congrats-Flow-GENEROUS"
  "/Users/USER/code/repos/backend-restructing"
  "/Users/USER/code/repos/vettedai-audition-supabase-version"
  "/Users/USER/code/repos/vfacoffeechat"
  "/Users/USER/code/repos/nts-opportunity-hour-digest"
)

for repo in "${REPOS[@]}"; do
  echo "=== $(basename $repo) ==="
  cd "$repo"

  # Reset submodule if it has local changes (they've been synced already)
  cd submodules/skill-master && git checkout -- . 2>/dev/null; cd ../..

  # Update submodule to latest
  git submodule update --remote submodules/skill-master
done
```

If a repo fails (dirty submodule, etc.), report the error but continue with the rest.

#### Step 5: Report results

```
Synced: [skill-name]
  skill-master: committed + pushed (commit abc1234)

  Updated repos:
    vetted-congrats-Flow-GENEROUS  OK
    backend-restructing            OK
    vettedai-audition-supabase-version  OK
    vfacoffeechat                  OK
    nts-opportunity-hour-digest    OK
```

---

## Mode: pull

Update the skill-master submodule in the CURRENT repo only.

### When to use
- User says "pull latest skills", "update skills"
- After someone else pushed to skill-master

### Workflow

```bash
# In the current repo
cd submodules/skill-master && git checkout -- . 2>/dev/null; cd ../..
git submodule update --remote submodules/skill-master
```

Show which skills changed:
```bash
cd submodules/skill-master
git log --oneline HEAD@{1}..HEAD 2>/dev/null
```

---

## Mode: propagate

Update the skill-master submodule in ALL consuming repos (not just the current one).

### When to use
- After pushing to skill-master from any source
- User says "update all repos", "propagate skills"

### Workflow

Same as Step 4 of sync mode — iterate through all repos and update the submodule. Report success/failure for each.

---

## Mode: copy

Copy a skill to a repo that does NOT use the submodule pattern.

### When to use
- Target repo doesn't have `submodules/skill-master`
- One-off skill copy

### Workflow

```bash
TARGET="$1"
SKILL="$2"
SKILL_MASTER="/Users/USER/code/repos/skill-master"

mkdir -p "$TARGET/.agent/skills"
cp -r "$SKILL_MASTER/.agent/skills/$SKILL" "$TARGET/.agent/skills/"

# Set up IDE symlinks if needed
if [ ! -L "$TARGET/.claude/skills" ]; then
  mkdir -p "$TARGET/.claude"
  cd "$TARGET" && ln -s ../.agent/skills .claude/skills
fi
```

---

## Error Handling

| Error | Resolution |
|-------|------------|
| Submodule has local changes | `git checkout -- .` in the submodule before updating |
| skill-master push rejected (behind remote) | `git stash && git pull --rebase && git stash pop && git push` |
| Repo not found at expected path | Skip, warn user, suggest updating the repo table |
| Skill exists in local but not in skill-master | Ask user: create new skill in skill-master, or local-only? |

## Important Notes

- **Always show diffs before syncing** — never silently overwrite skill-master
- **Always commit with a descriptive message** — the skill name + what changed
- **The consuming repos table must be kept up to date** — when a new repo adds the submodule, add it here
- **Local-only skills** (in `.claude/skills/` but not in skill-master) are left untouched — sync only operates on skills that exist in both places
