---
name: db-schema-oracle
description: Mandatory grounding source for database operations. Use this before writing SQL, creating Supabase migrations, or querying projects, opportunities, or audition_answers to prevent schema hallucinations.
---

# DB Schema Oracle

You are the guardian of data integrity for the VettedAI dual-platform architecture. Your primary function is to prevent Signal Collapse by ensuring every database operation is grounded in the established schema rather than predictive hallucinations.

## When to Use This Skill

- **Schema Mapping:** Determining if a field resides in the Vetted 'projects' table or the Congrats 'opportunities' table.
- **Migration Logic:** Before generating any DDL (Data Definition Language) statements like 'ALTER TABLE' or 'CREATE TABLE'.
- **API Development:** When modifying the Bridge API ('server.js') to ensure accurate field mapping between platforms.
- **Error Diagnosis:** Debugging 'Column not found', 'Relation does not exist', or Type Mismatch errors.

## Truth Sources (Grounding Files)

Before proposing or executing code, you must read and reference the following local files:
1. **Congrats (Talent-facing Side):** `references/congrats_schema.md`
2. **Vetted (Employer-facing Side):** `references/vetted_schema.md`

## Standard Operating Procedures (SOPs)

### 1. The Verification Loop
- **Step A:** Identify the required data field (e.g., Job Title).
- **Step B:** Cross-reference the relevant Oracle file for the exact table and column name (e.g., 'projects.role_title').
- **Step C:** If the requested field does not exist in the Oracle file, you are prohibited from assuming its existence. You must halt and notify the user: "The current schema does not contain [Column Name] in the [Table Name] table. Propose a migration or identify an existing alternative."


## 2. Security & Integrity Guardrails

- **Row Level Security (RLS):** Consult the 'rls' section of the Oracle file. Every query must include the appropriate 'auth.uid()' or 'user_id' filter to prevent data leakage.

## 3. Multi-Stage Audition Warning

**CRITICAL:** The `audition_submissions` table can have MULTIPLE rows for the same `(user_id, opportunity_id)` combination due to multi-stage auditions (experience stage + skills stage).

**NEVER use `.single()` with `user_id + opportunity_id` queries.** Use `.order().limit(1)` instead.

See: `backend/docs/MULTI_STAGE_AUDITION_PATTERNS.md` for the correct query patterns.
