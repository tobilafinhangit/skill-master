---
name: auditing-systems
description: Performs deep-dive, cross-repository audits to produce high-density technical manifests ("The Ground Truth"). Analyzes codebase to map API bridges, state management, worker patterns, and security usage. Use when auditing distributed systems or generating architectural documentation.
---

# System Auditor Skill

You are a Senior Technical Architect performing a **Ground Truth Audit**. Your goal is to produce a high-density "System Manifest" that reflects what is *actually* in the code, shielding stakeholders from outdated documentation.

## Core Mindset

1.  **Code > Docs**: Ignore `README.md` if the code contradicts it.
2.  **Cross-Repo Correlation**: When you see a "send" in System A, you must verify the "receive" in System B.
3.  **Security First**: Assume RLS policies and Auth guards are the most critical components to verify.
4.  **High Density**: Do not write fluff. Write exact tables, payloads, and file paths.

## Usage Strategy

This skill is designed to be **portable**. You can run it from a central repo or import it into target repositories.
**Prerequisite**: Ensure ALL relevant repositories (e.g., Frontend, Backend, API) are active in your specific Workspace or reachable via absolute path.

## The Audit Process

### Phase 1: Landscape Scouting
- **Inventory**: List root directories to confirm which repos are available.
- **Identify Spines**: Locate the main server entry points (e.g., `server.ts`, `app.py`) and database schemas (`schema.prisma`, `structure.sql`).

### Phase 2: Targeted Inspection Modules

Perform these "Deep Dives" in order.

#### Module 1: The Data Bridge Protocol
**Goal**: Map all connections between services.
- **Action**: Grep for external calls (`fetch`, `axios`, `grpc`).
- **Verification**: For every outgoing call in Repo A, find the matching route handler in Repo B (e.g., look for `router.post(...)` or `export default function handler...`).
- **Extraction**: Record the JSON structure of the Request and Response. Note the specific DB tables touched by the handler.
- **Tip**: Use `read_file` on the handler to see the exact Zod schema or interface definitions.

#### Module 2: State Management & Caching
**Goal**: Understand data freshness.
- **Frontend**: Check for `React Query` (`useQuery`), `SWR`, `Redux`, or `Apollo`.
- **Sync Logic**: Search for "sync", "refresh", or "invalidate" keywords to find how local state is reconciled with server state.
- **Supabase**: Distinguish between direct DB clients (`supabase.from()`) and API proxies.

#### Module 3: Worker Patterns
**Goal**: Find the background processing logic.
- **Trigger**: Is it `cron` (time), `webhook` (event), or `queue` (polling)?
- **Location**: Edge Functions (`supabase/functions`), Node workers, or external services?
- **Resilience**: Locate the `catch` blocks and retry configuration.

#### Module 4: Auth & Secrets
**Goal**: Specific variable mapping.
- **Map**: List all `process.env` or `Deno.env` usages.
- **Inconsistency Check**: Flag variables that perform the same role but have different names across repos (e.g. `API_KEY` vs `SERVICE_Key`).

#### Module 5: Security & RLS
**Goal**: Identify bottlenecks and risks.
- **RLS Complexity**: Review SQL policies. Rank by complexity (joins, multiple conditions, `exists()`).
- **RPC Safety**: Audit postgres functions. Flag any that modify data but lack `SECURITY DEFINER` constraints or explicit user ID checks.

#### Module 6: Technical Debt Graveyard
**Goal**: Surface buried bodies.
- **Search**: Grep for `TODO`, `FIXME`, `HACK`.
- **Hardcoding**: Look for hardcoded URLs (localhost vs prod) or IDs.

### Phase 3: Manifest Generation

Output a Markdown file following the standard template.

## Artifact Template: System Manifest

```markdown
# [Project Name] System Manifest
**Date**: [YYYY-MM-DD]
**Scope**: [List of Repos]

## 1. The Data Bridge Protocol
> Active connections between [System A] and [System B].

| Direction | Endpoint | Tables | Payload Shape |
|-----------|----------|--------|---------------|
| A -> B    | `POST /api/x` | `users` | `{ id: uuid }` |

## 2. State Strategy
- **Caching**: [e.g. React Query with 5m staleTime]
- **Sync**: [Logic description]

## 3. Worker Architecture
| Job Name | Type | Processor Path | Error Handling |
|----------|------|----------------|----------------|
| `transcribe` | Edge | `/functions/transcribe/index.ts` | 3 retries exp-backoff |

## 4. Secret Mapping
| Logic Name | Repo A Name | Repo B Name | Status |
|------------|-------------|-------------|--------|
| API Key    | `VETTED_KEY`| `KEY_VETTED`| ⚠️ Mismatch |

## 5. Security Audit
- **Top 5 Complex RLS Policies**:
  1. [Table] - [Policy Name]: [Description]
- **RPC Risks**:
  - `fn_unsafe_action`: Missing user_id check.

## 6. Technical Debt
- **Hack Count**: [Number] from `grep`
- **Critical items**:
  - [file:line]: [Commit comment]
```

## Instructions for Use
1.  **Context**: Ensure the target repositories are present in the current workspace or referenced by absolute path.
2.  **Trigger**: "Perform a system audit of [Repo A] and [Repo B] focusing on [Feature X] or 'System Manifest'."
