---
name: pulling-skills
description: Scans a target project's tech stack and recommends relevant skills from skill-master, then installs them via git submodule + symlinks. Use when bootstrapping a new project with skills, onboarding a repo to the skill ecosystem, or running "pull skills into this project".
version: 1.0.0
license: MIT
---

# Pull Skills from Skill-Master

The reverse of `distribute-skill`. Run this FROM the target project to scan its tech stack, get skill recommendations, and install them via git submodule + per-skill symlinks.

## When to Use This Skill

- Setting up a new project and want relevant skills
- Onboarding an existing repo to the skill ecosystem
- User says "pull skills into this project" or "what skills do I need?"
- Bootstrapping after cloning a repo that doesn't have skills yet

## Chicken-and-Egg Bootstrap

This skill lives in skill-master but runs from target repos. First-time setup options:

1. **Manual copy** (simplest): Copy this single skill file into the target repo, run it, and it will set up the submodule + symlinks for everything else.
2. **Direct invocation**: If the user has skill-master cloned locally, reference its path directly.

## Workflow

### Phase 1: Project Scan

Detect the project's tech stack by checking for these files:

```bash
# Run all checks in parallel for speed
ls package.json 2>/dev/null          # Node.js / JS ecosystem
ls requirements.txt pyproject.toml setup.py Pipfile 2>/dev/null  # Python
ls Cargo.toml 2>/dev/null            # Rust
ls go.mod 2>/dev/null                # Go
ls supabase/config.toml 2>/dev/null  # Supabase
ls docker-compose.yml Dockerfile 2>/dev/null  # Docker
ls .github/workflows/*.yml 2>/dev/null  # GitHub Actions CI/CD
ls tsconfig.json 2>/dev/null         # TypeScript
ls .env .env.example 2>/dev/null     # Environment config
```

**Stack detection heuristics:**

| Signal | Detected As |
|--------|-------------|
| `supabase/` dir or `@supabase/supabase-js` in package.json | Supabase project |
| `next.config.*` or `"next"` in package.json | Next.js |
| `"react"` in package.json | React frontend |
| `"express"` or `"fastify"` or `"hono"` in package.json | API server |
| SQL files, `migrations/` dir, `prisma/`, `drizzle/` | Database project |
| Multiple `package.json` files or `pnpm-workspace.yaml` | Monorepo |
| `supabase/functions/` dir | Supabase Edge Functions |
| `.github/workflows/` | CI/CD pipeline |
| `openapi.yaml` or `swagger.json` | API-first project |

Build a `PROJECT_PROFILE` object with boolean flags:
- `has_supabase`, `has_database`, `has_api`, `has_frontend`, `has_ci`, `has_tests`, `is_monorepo`, `has_edge_functions`

### Phase 2: Locate Skill-Master

Check in this order:
1. `submodules/skill-master/.agent/skills/` (already a submodule)
2. Ask the user for the path if not found

If skill-master is not yet a submodule, note this for Phase 4.

Read each `SKILL.md` frontmatter to build the available skills inventory.

### Phase 3: Recommend Skills

Use this matching matrix to categorize skills:

#### Essential (every project benefits)

| Skill | Why |
|-------|-----|
| `troubleshooting` | Universal debugging workflow |
| `planning` | Structured approach to multi-step tasks |
| `brainstorming` | Explore intent before building |
| `impact-analysis` | Prevent regressions before changing shared code |
| `learning-from-corrections` | Build project memory from mistakes |
| `executing-plans` | Execute plans with review checkpoints |

#### Recommended (if project profile matches)

| Skill | Condition |
|-------|-----------|
| `test-driven-development` | `has_tests` OR any testable codebase |
| `pr-verification` | `has_ci` OR team project |
| `requesting-code-review` | Team project or complex codebase |
| `finishing-a-development-branch` | Git-based workflow |
| `generating-release-notes` | Projects with releases or deployments |
| `grooming-architect` | Projects with product/engineering split |
| `using-git-worktrees` | Complex feature work needing isolation |
| `subagent-driven-development` | Large implementation tasks |

#### Stack-Specific (only if stack detected)

| Skill | Condition |
|-------|-----------|
| `supabase-postgres-expert` | `has_supabase` OR `has_database` (Postgres) |
| `supabase-solution-architect` | `has_supabase` |
| `recovering-supabase-env-vars` | `has_supabase` |
| `db-schema-oracle` | `has_supabase` OR `has_database` |
| `api-parity-auditor` | `has_api` AND migration/comparison context |
| `verifying-apis` | `has_api` |
| `auditing-systems` | `is_monorepo` OR multi-repo architecture |

#### Meta (skill ecosystem management)

| Skill | Condition |
|-------|-----------|
| `creating-skills` | User wants to author new skills |
| `distribute-skill` | User manages multiple repos |
| `skill-strategist` | User wants skill recommendations later |
| `pulling-skills` | Already installed (this skill) |

#### Present Recommendations to User

Format output like this:

```
## Skill Recommendations for [project-name]

Detected: [Supabase, React, TypeScript, GitHub Actions, ...]

### Essential (6 skills)
- [x] troubleshooting — Universal debugging
- [x] planning — Multi-step task structure
- [x] brainstorming — Explore before building
- [x] impact-analysis — Prevent regressions
- [x] learning-from-corrections — Build project memory
- [x] executing-plans — Execute with checkpoints

### Recommended (N skills)
- [x] test-driven-development — You have tests
- [x] pr-verification — CI detected
- [ ] grooming-architect — Uncheck if solo project

### Stack-Specific (N skills)
- [x] supabase-postgres-expert — Supabase detected
- [x] db-schema-oracle — Database detected
- [ ] api-parity-auditor — Only if migrating APIs

### Meta
- [ ] creating-skills — Author new skills
- [ ] skill-strategist — Future recommendations
```

**Ask the user to confirm or modify the selection before proceeding.**

### Phase 4: Installation

#### Step 1: Add skill-master as git submodule (if needed)

```bash
# Check if submodule already exists
git submodule status 2>/dev/null | grep skill-master

# If not found, add it
mkdir -p submodules
git submodule add git@github.com:tobilafinhangit/skill-master.git submodules/skill-master
git submodule update --init --recursive
```

#### Step 2: Create .agent/skills directory

```bash
mkdir -p .agent/skills
```

#### Step 3: Create per-skill symlinks

For each selected skill, create a symlink pointing into the submodule:

```bash
# Template for each skill
ln -s ../../submodules/skill-master/.agent/skills/[SKILL_NAME] .agent/skills/[SKILL_NAME]
```

Example batch:
```bash
SKILLS="troubleshooting planning brainstorming impact-analysis"
for skill in $SKILLS; do
    ln -s "../../submodules/skill-master/.agent/skills/$skill" ".agent/skills/$skill"
done
```

**Important**: Use relative paths (`../../submodules/...`) so symlinks work regardless of where the repo is cloned.

#### Step 4: Set up workspace-level symlinks for multi-IDE support

```bash
# Check if they already exist
ls -la .cursor/skills .claude/skills 2>/dev/null

# Create if missing
mkdir -p .cursor .claude
ln -s ../.agent/skills .cursor/skills
ln -s ../.agent/skills .claude/skills
```

#### Step 5: Handle local-only skills

If the target repo has local skills (not from skill-master) in `.agent/skills/`, they will coexist alongside the symlinks. No conflict.

#### Step 6: Verify installation

```bash
# Check submodule
git submodule status | grep skill-master

# Check symlinks resolve correctly
for skill in .agent/skills/*/; do
    name=$(basename "$skill")
    if [ -L ".agent/skills/$name" ]; then
        target=$(readlink ".agent/skills/$name")
        echo "✓ $name → $target"
        # Verify the symlink target actually exists
        ls ".agent/skills/$name/SKILL.md" > /dev/null 2>&1 && echo "  SKILL.md: found" || echo "  ⚠ SKILL.md: NOT FOUND"
    else
        echo "• $name (local skill, not symlinked)"
    fi
done

# Check workspace symlinks
readlink .cursor/skills   # Should show: ../.agent/skills
readlink .claude/skills   # Should show: ../.agent/skills
```

#### Step 7: Report results

```
✅ Pulled [N] skills into [project-name]

Installed via symlink (from skill-master submodule):
  • troubleshooting
  • planning
  • brainstorming
  • ...

Local skills (unchanged):
  • [any-existing-local-skill]

Multi-IDE support:
  • .agent/skills/ (Antigravity) ✓
  • .cursor/skills/ → .agent/skills/ ✓
  • .claude/skills/ → .agent/skills/ ✓

To update skills later:
  cd submodules/skill-master && git pull && cd ../..

To add more skills:
  /pulling-skills
```

## Updating Skills

Since skills are symlinked to the submodule, updating is just:

```bash
cd submodules/skill-master
git pull origin main
cd ../..
git add submodules/skill-master
git commit -m "chore: update skill-master submodule"
```

## Adding a Single Skill Later

If the user wants to add one more skill after initial setup:

```bash
ln -s "../../submodules/skill-master/.agent/skills/[NEW_SKILL]" ".agent/skills/[NEW_SKILL]"
```

No need to re-run the full workflow.

## Removing a Skill

```bash
rm .agent/skills/[SKILL_NAME]  # Removes symlink only, not the source
```
