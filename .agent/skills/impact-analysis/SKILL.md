---
name: impact-analysis
description: Analyzes downstream impact of code changes BEFORE implementation to prevent regressions. Use when modifying shared functions, hooks, APIs, database schemas, types, or any code with multiple consumers. Prevents the "hammer everything" myopia of AI agents.
---

# Pre-Change Impact Analysis

Stop. Before you touch that shared code, **map the blast radius**.

## When to Use This Skill

**Code-Level Changes:**
- Modifying a shared function, hook, or utility used by multiple components
- Changing an API signature (parameters, return types)
- Refactoring a type definition or interface with external consumers
- Renaming or moving code that might be imported elsewhere

**Database/Schema Changes:**
- Adding, renaming, or removing columns
- Modifying constraints (NOT NULL, UNIQUE, foreign keys)
- Changing views, functions, or triggers
- Updating RLS policies

**API/Endpoint Changes:**
- Modifying request/response shapes
- Changing endpoint paths or methods
- Deprecating or removing endpoints

**Config/Environment Changes:**
- Renaming or removing environment variables
- Changing feature flag behavior
- Modifying deployment configurations

---

## The Problem This Skill Solves

AI agents tend to:
1. Fix what's in front of them without mapping dependencies
2. Create "V2" duplicates instead of proper migrations  
3. React to errors one-by-one instead of understanding the graph upfront
4. Break callers by changing contracts without checking consumers first

**This skill forces upfront impact discovery before any changes.**

---

## Core Workflow (All Change Types)

### Phase 1: Consumer Discovery

Identify everything that depends on what you're changing.

### Phase 2: Contract Analysis

Document what each consumer expects from the current implementation.

### Phase 3: Risk Assessment

| Risk Level | Criteria | Action |
|------------|----------|--------|
| 🟢 **Safe** | 0 breaking consumers | Proceed with change |
| 🟡 **Moderate** | 1-3 consumers need updates | Update all in same PR |
| 🔴 **High** | 4+ consumers OR diverse patterns | Migration strategy needed |

### Phase 4: Decision Gate

- **A. In-Place Update** — Update everything together
- **B. Deprecate & Migrate** — Introduce new alongside old, migrate incrementally
- **C. Abort & Redesign** — Step back, rethink the abstraction

---

## Specialized: Code-Level Changes

### Discovery Commands

```bash
# Functions/hooks/types
grep -rn "<symbol>" --include="*.ts" --include="*.tsx" --include="*.js" .

# Python
grep -rn "<symbol>" --include="*.py" .

# Go
grep -rn "<symbol>" --include="*.go" .
```

### Consumer Manifest Template

```markdown
## Consumer Manifest: `useFilteredCandidates`

| File | Line | Usage Pattern |
|------|------|---------------|
| `pages/Candidates.tsx` | 45 | Destructures `{ candidates, filters }` |
| `pages/Shortlist.tsx` | 23 | Uses only `candidates` |
| `pages/Dossiers.tsx` | 67 | Passes custom `FilterOptions` type |
```

### Compatibility Matrix

```markdown
| Consumer | Current Contract | Breaking? | Migration Path |
|----------|------------------|-----------|----------------|
| Candidates.tsx | `{ candidates, filters }` | ✅ Yes | Update destructure |
| Shortlist.tsx | `{ candidates }` | ❌ No | None needed |
```

---

## Specialized: Database/Schema Changes

### Discovery Checklist

Before changing a table/column:

- [ ] **Views**: `SELECT * FROM pg_views WHERE definition LIKE '%table_name%'`
- [ ] **Functions**: `SELECT proname FROM pg_proc WHERE prosrc LIKE '%column_name%'`
- [ ] **Triggers**: Check `pg_trigger` for dependencies
- [ ] **RLS Policies**: `SELECT * FROM pg_policies WHERE tablename = 'table_name'`
- [ ] **ORM Models**: `grep -rn "table_name" --include="*.ts" --include="*.py"`
- [ ] **Migrations**: Check if other pending migrations touch same objects
- [ ] **Foreign Keys**: `SELECT * FROM information_schema.referential_constraints`

### Schema Consumer Manifest

```markdown
## Consumer Manifest: `candidates.status` column

| Consumer Type | Name | Impact |
|---------------|------|--------|
| View | `user_applications_view` | Uses in CASE statement |
| RLS Policy | `candidates_select` | Filters on status |
| Function | `fn_update_pipeline` | Sets status value |
| ORM Model | `models/Candidate.ts` | Maps to `status` field |
| Frontend | `CandidateCard.tsx` | Displays status badge |
```

### Database Risk Modifiers

| Factor | Risk Increase |
|--------|---------------|
| Column used in WHERE clause | +1 level |
| Column has NOT NULL constraint | +1 level |
| Table has RLS policies | +1 level |
| Column referenced by FK | +1 level (may need cascade) |
| Production data exists | +1 level (needs data migration) |

### Migration Patterns

**Adding Nullable Column**: 🟢 Safe
```sql
ALTER TABLE t ADD COLUMN new_col TEXT;
```

**Adding NOT NULL Column**: 🟡 Moderate — Needs default or backfill
```sql
ALTER TABLE t ADD COLUMN new_col TEXT NOT NULL DEFAULT 'pending';
```

**Renaming Column**: 🔴 High — All consumers break
```sql
-- Step 1: Add new column
-- Step 2: Backfill data  
-- Step 3: Update all consumers
-- Step 4: Drop old column (separate migration)
```

**Removing Column**: 🔴 High
```sql
-- Step 1: Remove all code references first
-- Step 2: Mark column as deprecated (add comment)
-- Step 3: Drop column after deployment confirms no usage
```

---

## Specialized: API/Endpoint Changes

### Discovery Checklist

Before changing an API endpoint:

- [ ] **Frontend Calls**: `grep -rn "endpoint-path" --include="*.ts" --include="*.tsx"`
- [ ] **Service Clients**: Check SDK/client libraries
- [ ] **External Consumers**: Webhooks, partner integrations, mobile apps
- [ ] **API Docs**: OpenAPI/Swagger spec references
- [ ] **Tests**: API integration tests calling this endpoint
- [ ] **Postman/Insomnia**: Shared collection references

### API Consumer Manifest

```markdown
## Consumer Manifest: `POST /api/audition/start`

| Consumer | Location | Request Shape | Response Usage |
|----------|----------|---------------|----------------|
| Frontend | `useAuditionStages.ts:45` | `{ projectId, userId }` | Uses `submission_id` |
| Mobile App | External | Same | Same |
| VettedAI Webhook | External | Unknown | Unknown (⚠️ verify) |
```

### API Breaking Change Signals

| Change | Breaking? |
|--------|-----------|
| Add optional request field | ❌ No |
| Add response field | ❌ No |
| Remove/rename request field | ✅ Yes |
| Remove/rename response field | ✅ Yes |
| Change field type | ✅ Yes |
| Change HTTP method | ✅ Yes |
| Change endpoint path | ✅ Yes |

### API Versioning Decision

If breaking changes are unavoidable:

```markdown
## Versioning Strategy

| Option | Pros | Cons |
|--------|------|------|
| URL versioning `/v2/endpoint` | Clear, discoverable | URL clutter |
| Header versioning `Accept: v2` | Clean URLs | Less visible |
| Additive changes only | No breaking | May bloat API |
```

---

## Specialized: Environment/Config Changes

### Discovery Checklist

- [ ] **Code References**: `grep -rn "ENV_VAR_NAME" .`
- [ ] **Docker/Compose**: `grep -rn "ENV_VAR_NAME" docker*.yml`
- [ ] **CI/CD**: `.github/workflows/*.yml`, `vercel.json`, etc.
- [ ] **Documentation**: README, deployment guides
- [ ] **Secrets Manager**: Vault, AWS SSM, Vercel env settings
- [ ] **Local Dev**: `.env.example`, `.env.local`

### Config Consumer Manifest

```markdown
## Consumer Manifest: `SUPABASE_URL`

| Location | Type | Fallback? |
|----------|------|-----------|
| `lib/supabase.ts` | Runtime | ❌ Throws |
| `docker-compose.yml` | Build | Uses default |
| `.github/workflows/deploy.yml` | CI/CD | ❌ None |
| `README.md` | Docs | N/A |
```

---

## Anti-Patterns This Skill Prevents

### ❌ The V2 Trap
```typescript
// BAD: Now you maintain two APIs forever
export function useFilteredCandidates() { ... }
export function useFilteredCandidatesV2() { ... }
```

### ❌ Reactive Debugging
```
// BAD: Fix error in FileA → causes error in FileB → fix that → error in FileC...
```

### ❌ Type Proliferation
```typescript
// BAD: Same concept, multiple incompatible types
type CandidateFilterState = { ... }
type CandidateFilterOptions = { ... }
type FilterConfig = { ... }
```

### ❌ Schema Changes Without Checking Views
```sql
-- BAD: Rename column, breaks 3 views you didn't check
ALTER TABLE candidates RENAME COLUMN status TO state;
```

### ❌ Removing Env Var Without Checking CI
```yaml
# BAD: Remove from code but CI still injects it (or vice versa)
```

---

## Master Checklist

Before making any shared change:

- [ ] Identified change type (code / schema / API / config)
- [ ] Ran appropriate discovery commands
- [ ] Created consumer manifest
- [ ] Built compatibility matrix
- [ ] Assigned risk level (🟢/🟡/🔴)
- [ ] Chose strategy (in-place / deprecate / redesign)
- [ ] If 🟡/🔴: Created migration plan before touching code

---

## Integration with Other Skills

| After Impact Analysis | Use This Skill |
|-----------------------|----------------|
| Risk is 🟢 Safe | Proceed to implementation |
| Risk is 🟡 Moderate | Use `planning` skill to sequence updates |
| Risk is 🔴 High | Use `brainstorming` skill to redesign |
| Database migration needed | Use `/create-migration` workflow |
| API versioning needed | Use `planning` for migration roadmap |

---

## Quick Reference

```
1. IDENTIFY change type (code/schema/API/config)
2. RUN discovery for that type
3. LIST all consumers in manifest
4. ANALYZE each consumer's contract
5. CLASSIFY risk (🟢/🟡/🔴)
6. DECIDE: in-place | deprecate | redesign
7. PROCEED only after checklist complete
```
