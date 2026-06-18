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

### How consumers pick up updates (the submodule is PINNED)

Pushing the canonical (`skill-master` main) does **NOT** auto-propagate. Each consumer repo pins a
specific submodule commit and keeps it until someone *deliberately* bumps — there is no
notification. So the **editor** owns propagation (run this skill's `sync`/`propagate` mode after any
skill edit); consumers don't discover it on their own.

- A consumer picks up the latest manually with `git submodule update --remote submodules/skill-master`,
  then commits the pointer bump — but **only on an integration branch** (see below).
- Diagnostic for "is a repo stale?": `git ls-tree HEAD submodules/skill-master` (pinned commit) vs
  `git -C submodules/skill-master rev-parse origin/main`.
- `.agent/skills/<skill>` must be a **symlink** into `submodules/skill-master/.agent/skills/<skill>`,
  not a real-directory copy — a copy silently shadows the canonical and drifts. Fix:
  `rm -rf <skill> && ln -s ../../submodules/skill-master/.agent/skills/<skill> <skill>`.

### Pointer commits are BRANCH-AWARE — never pollute a feature PR

`git submodule update --remote` updates the working tree but leaves the pointer **uncommitted**.
Whether to commit it depends on the consumer's current branch:

- **On an integration branch** (`main`, `lovable-staging`, `verify-deployments`,
  `backend-verify-deployment`): commit + push the pointer bump (set per-repo author identity first;
  the canonical is already pushed, so submodule-first ordering is satisfied).
- **On a feature branch** (`feat/*`, `fix/*`, anything mid-work): do **NOT** commit the pointer — it
  would land inside that branch's PR diff. Update the working tree, then **report** that the pointer
  is updated-but-uncommitted and tell the user to bump it on the repo's integration branch (or via
  that repo's normal feature→integration flow; some repos, e.g. Congrats, require a PR, not a direct
  commit — see `sister-repo-branch-conventions`).

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

INTEGRATION_BRANCHES="main lovable-staging verify-deployments backend-verify-deployment qa-mirror"

for repo in "${REPOS[@]}"; do
  echo "=== $(basename $repo) ==="
  cd "$repo"

  # Reset submodule if it has local changes (they've been synced already)
  cd submodules/skill-master && git checkout -- . 2>/dev/null; cd ../..

  # Update submodule working tree to latest skill-master main
  git submodule update --remote submodules/skill-master

  # Persist the pointer ONLY on an integration branch — never pollute a feature PR.
  branch=$(git rev-parse --abbrev-ref HEAD)
  if git diff --quiet submodules/skill-master; then
    echo "  pointer already current — nothing to commit"
  elif echo " $INTEGRATION_BRANCHES " | grep -q " $branch "; then
    git add submodules/skill-master
    git -c user.email="tobi@venturefor.africa" -c user.name="tobilafinhangit" \
      commit -q -m "chore(skills): bump skill-master submodule"
    git push    # confirm with the user before pushing shared branches
    echo "  pointer committed + pushed on integration branch '$branch'"
  else
    echo "  ⚠️ working tree updated but pointer NOT committed (on feature branch '$branch')."
    echo "     Bump it on this repo's integration branch — for PR-gated repos (e.g. Congrats),"
    echo "     via the normal feature→integration flow. See sister-repo-branch-conventions."
  fi
done
```

If a repo fails (dirty submodule, etc.), report the error but continue with the rest. **Never**
commit a pointer bump onto a feature branch — it lands inside that branch's PR. On a feature branch,
leave the working-tree update and report the uncommitted pointer for the user to persist on an
integration branch.

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
- **The submodule is pinned — updates do NOT auto-arrive.** Consumers stay on their pinned commit until deliberately bumped; the editor owns propagation (see "How consumers pick up updates" above)
- **Pointer commits are branch-aware** — commit + push the bump only on an integration branch; on a feature branch, leave it uncommitted and report it (committing would pollute that branch's PR)
- **Skills must be symlinks, not copies** — a real-directory copy under `.agent/skills/` silently shadows the canonical and drifts; convert it to a symlink into the submodule
