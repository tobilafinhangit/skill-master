---
name: pr-verification
description: Verifies pull requests are safe to merge by detecting regressions, destructive patterns, and breaking changes. Use when reviewing PRs from junior engineers, before merging feature branches, or when you need to verify a PR doesn't break existing functionality.
---

# PR Verification

Stop. Before you approve that PR, **verify it doesn't break anything**.

## When to Use This Skill

- Reviewing a PR from a junior or mid-level engineer
- Before merging any feature branch to main
- When a PR touches shared code (utilities, hooks, APIs)
- When you see deletions or modifications in the diff
- Anytime you want to verify a PR is additive, not destructive

---

## Core Workflow

```
1. FETCH PR diff against target branch
2. CATEGORIZE changes (additions/modifications/deletions)
3. IDENTIFY high-risk patterns
4. DISCOVER consumers of modified/deleted code
5. BUILD regression risk matrix
6. GENERATE verdict (Safe / Needs Review / Block)
```

---

## Phase 1: Fetch & Categorize Changes

### Get the Diff

```bash
# Compare PR branch against target (usually main)
git fetch origin
git diff origin/main...HEAD --stat
git diff origin/main...HEAD --name-status
```

### Categorize by Risk

| Status | Meaning | Risk Level |
|--------|---------|------------|
| `A` | Added (new file) | 🟢 Low |
| `M` | Modified | 🟡 Medium |
| `D` | Deleted | 🔴 High |
| `R` | Renamed | 🟡 Medium |

### Create Change Manifest

```markdown
## Change Manifest

### 🟢 Added Files (Low Risk)
- `src/components/NewFeature.tsx`
- `src/utils/newHelper.ts`

### 🟡 Modified Files (Medium Risk)
- `src/hooks/useAuth.ts`
- `src/api/endpoints.ts`

### 🔴 Deleted Files (High Risk)
- `src/legacy/oldComponent.tsx`
```

---

## Phase 2: Detect Destructive Patterns

For each **Modified** or **Deleted** file, check for these red flags:

### Destructive Pattern Checklist

- [ ] **Removed exports** — Was a function/component/type exported before but not now?
- [ ] **Changed function signatures** — Were parameters added, removed, or reordered?
- [ ] **Changed return types** — Does the function return something different?
- [ ] **Removed properties** — Were object properties/interface fields removed?
- [ ] **Renamed without migration** — Was something renamed but callers not updated?
- [ ] **Deleted files** — Are deleted files still imported elsewhere?

### Detection Commands

```bash
# Find what was exported before (on main)
git show origin/main:src/utils/myFile.ts | grep "^export"

# Find what's exported now
grep "^export" src/utils/myFile.ts

# Compare to find removed exports
diff <(git show origin/main:src/utils/myFile.ts | grep "^export") \
     <(grep "^export" src/utils/myFile.ts)
```

### Signature Change Detection

```bash
# View function signature changes
git diff origin/main...HEAD -- src/utils/myFile.ts | grep -E "^[-+].*function|^[-+].*const.*=.*\(|^[-+].*export"
```

---

## Phase 3: Consumer Discovery

For each modified/deleted export, find all consumers.

### Discovery Commands

```bash
# Find all imports of a file
grep -rn "from ['\"].*myFile" --include="*.ts" --include="*.tsx" .

# Find all usages of a specific function
grep -rn "functionName" --include="*.ts" --include="*.tsx" .

# Find all usages of a deleted file
grep -rn "deletedFileName" --include="*.ts" --include="*.tsx" .
```

### Consumer Manifest Template

```markdown
## Consumer Manifest: `useAuth` hook

| File | Line | Usage Pattern | Breaking? |
|------|------|---------------|-----------|
| `pages/Login.tsx` | 23 | `const { user, login } = useAuth()` | ✅ Yes — `login` removed |
| `pages/Dashboard.tsx` | 15 | `const { user } = useAuth()` | ❌ No |
| `components/Header.tsx` | 8 | `const { logout } = useAuth()` | ❌ No |
```

---

## Phase 4: Build Regression Risk Matrix

| Changed Item | Type | Consumers | Breaking? | Risk |
|--------------|------|-----------|-----------|------|
| `useAuth.login()` | Removed export | 3 files | ✅ Yes | 🔴 High |
| `formatDate()` | Changed signature | 5 files | ✅ Yes | 🔴 High |
| `Button.tsx` | Added prop | 12 files | ❌ No (additive) | 🟢 Low |
| `legacy/old.ts` | Deleted file | 0 files | ❌ No | 🟢 Low |

### Risk Level Definitions

| Level | Criteria | Action |
|-------|----------|--------|
| 🟢 **Safe** | All changes additive, no consumers broken | Approve |
| 🟡 **Needs Review** | 1-3 consumers affected, updates included in PR | Review carefully |
| 🔴 **Block** | 4+ consumers affected OR breaking changes without updates | Request changes |

---

## Phase 5: Generate Verdict

### Verdict Template

```markdown
# PR Verification Report

## Summary
**Verdict: [🟢 SAFE / 🟡 NEEDS REVIEW / 🔴 BLOCK]**

## Change Overview
- **Added**: X files
- **Modified**: Y files  
- **Deleted**: Z files

## Risk Assessment

### High Risk Items
| Item | Issue | Affected Files |
|------|-------|----------------|
| `useAuth.login` | Removed without updating consumers | `Login.tsx`, `Signup.tsx` |

### Medium Risk Items
| Item | Issue | Affected Files |
|------|-------|----------------|
| `formatDate` | Signature changed (new required param) | `Dashboard.tsx` |

### Verified Safe
- ✅ `NewFeature.tsx` — New file, no existing dependencies
- ✅ `Button.tsx` — Added optional prop, backward compatible

## Recommendation
[Specific action items for the PR author]
```

---

## Quick Reference: Additive vs. Destructive

### ✅ Additive (Safe)
- Adding new files
- Adding new exports
- Adding optional parameters with defaults
- Adding new properties to objects/interfaces
- Adding new API endpoints

### ⚠️ Requires Verification
- Modifying existing functions (check signature)
- Renaming (check all consumers updated)
- Adding required parameters
- Changing return types

### ❌ Destructive (Dangerous)
- Removing exports
- Removing function parameters
- Removing object properties
- Deleting files
- Changing parameter order
- Changing types of existing fields

---

## Integration with Other Skills

| After PR Verification | Use This Skill |
|-----------------------|----------------|
| Found breaking changes | Use `impact-analysis` for deeper consumer mapping |
| Need detailed code review | Use `requesting-code-review` for quality |
| Need to fix issues | Ask PR author to update, then re-verify |

---

## Checklist for Reviewers

Before approving any PR:

- [ ] Ran `git diff --name-status` to see all changes
- [ ] Categorized changes by risk level
- [ ] For each Modified/Deleted file:
  - [ ] Checked for removed exports
  - [ ] Checked for signature changes
  - [ ] Found all consumers
  - [ ] Verified consumers are updated in this PR
- [ ] Generated regression risk matrix
- [ ] Verdict assigned with justification

---

## Red Flags — Always Block

- Deleted file still imported elsewhere
- Removed export still used by consumers
- Changed signature but callers not updated
- Type changes without consumer updates
- "Working on my machine" without understanding broader impact

---

## Example Workflow

```
You: Review PR #42 from junior dev

1. git diff origin/main...HEAD --name-status
   M  src/hooks/useAuth.ts
   D  src/utils/legacyHelper.ts
   A  src/components/NewFeature.tsx

2. Check legacyHelper.ts consumers:
   grep -rn "legacyHelper" --include="*.ts" .
   → Found in Dashboard.tsx:15, Settings.tsx:23

3. Build manifest:
   | Item | Issue | Risk |
   | legacyHelper.ts | Deleted, still imported by 2 files | 🔴 High |
   | useAuth.ts | Modified, checking signature... |
   | NewFeature.tsx | New file | 🟢 Low |

4. Verdict: 🔴 BLOCK
   "legacyHelper.ts is deleted but still imported by Dashboard.tsx and Settings.tsx. 
   Please either update those files or keep the legacy helper."
```
