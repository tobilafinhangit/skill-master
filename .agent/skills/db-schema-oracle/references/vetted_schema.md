Public Schema Deep Dive

Below is a comprehensive, AI-agent–friendly breakdown of all tables discovered in the public schema. For each table you'll find:

Purpose
Columns with type, nullability, and default
Constraints (PKs, FKs, unique, checks)
Active RLS policies (names and logic)
Enums & custom types used
Functions/Triggers of note (where relevant)
Note: RLS policies reference helper functions such as has_admin_access(), is_admin(), is_super_admin(), has_permission(), has_any_permission(), has_admin_or_ops_access(). These are not defined here but are used to gate access.

Table: projects
Purpose: Job/audition projects owned by recruiters.

Columns:
id uuid NOT NULL DEFAULT gen_random_uuid()
recruiter_id uuid NOT NULL
role_title text NOT NULL
company_name text NULL
job_description text NULL
job_summary text NULL
candidate_source text NULL
tier_name text NULL
tier_id int4 NULL
candidate_count int4 NULL DEFAULT 0
total_candidates int4 NULL DEFAULT 0
candidates_completed int4 NULL DEFAULT 0
completion_percentage numeric NULL DEFAULT 0
status text NULL DEFAULT 'pending_activation' CHECK status ∈ ['draft','active','ready','completed','archived']
payment_status text NULL DEFAULT 'pending'
hours_elapsed numeric NULL
sla_deadline timestamptz NULL
completed_at timestamptz NULL
created_at timestamptz NULL DEFAULT now()
updated_at timestamptz NULL DEFAULT now()
jd_fingerprint text NULL
evals_generated_at timestamptz NULL
evals_status text NULL DEFAULT 'pending' CHECK evals_status IS NULL OR evals_status ∈ ['pending','generating','completed','failed']
previous_status text NULL
regeneration_count int4 NULL DEFAULT 0
last_regeneration_at timestamptz NULL
free_regenerations_remaining int4 NULL DEFAULT 5
is_regenerating bool NULL DEFAULT false
congrats_audition_url text NULL
access_mode text NOT NULL DEFAULT 'restricted' CHECK access_mode ∈ ['restricted','public']
is_demo bool NULL DEFAULT true
congrats_job_url text NULL
has_invites_sent bool NOT NULL DEFAULT false
public_link_id uuid NULL UNIQUE
public_view_config jsonb NULL DEFAULT '{...}'::jsonb
public_password_hash text NULL
job_visibility bool NULL DEFAULT false
job_accessibility bool NULL DEFAULT false
audition_visibility bool NULL DEFAULT false
audition_accessibility bool NULL DEFAULT false
show_candidate_profile bool NULL DEFAULT false
ai_credits int4 NULL DEFAULT 100
Constraints:
PK: id
FKs:
projects.recruiter_id → recruiters.id
RLS:
Recruiters can view/update/delete own projects:
SELECT/UPDATE/DELETE USING (recruiter_id IN (SELECT recruiters.id WHERE recruiters.user_id = auth.uid()))
Recruiters can create own projects: INSERT WITH CHECK (recruiter_id IN (SELECT recruiters.id WHERE recruiters.user_id = auth.uid()))
Permission-based view/update/delete with has_permission('projects.view_all'|'projects.edit_any'|'projects.soft_delete')
Public discovery (anon/auth) for paid/non-demo:
Public can view projects for paid recruiters only: SELECT USING (EXISTS recruiter with is_paid_account=true) AND status not in [pending_activation,draft,pending]
Public can view non-demo projects: SELECT USING (is_demo=false AND status not in [pending_activation,draft,pending,archived]) AND (allow_unpaid_job_delivery=true OR recruiter.is_paid_account=true)

Table: project_stages
Purpose: Stores stage configuration for multi-stage auditions. Stages are stored separately from projects, not as a column.

IMPORTANT: Stages are NOT a column on the `projects` table. Query this table to get stages for a project.

Columns:
id uuid NOT NULL DEFAULT gen_random_uuid()
project_id uuid NOT NULL — FK → projects.id
stage_type audition_stage_type NOT NULL — Enum: 'experience', 'skills'
stage_order int4 NOT NULL DEFAULT 1 — CHECK (stage_order >= 1 AND stage_order <= 10)
is_enabled bool NOT NULL DEFAULT true
config jsonb NULL — Stage-specific configuration
created_at timestamptz NULL DEFAULT now()
updated_at timestamptz NULL DEFAULT now()

Constraints:
PK: id
FKs:
project_stages.project_id → projects.id
Unique: (project_id, stage_type) — One stage per type per project
Check: stage_order between 1 and 10

Enums:
audition_stage_type: 'experience', 'skills'

Example Query:
```sql
SELECT id, stage_type, stage_order, is_enabled, config
FROM project_stages
WHERE project_id = '<uuid>' AND is_enabled = true
ORDER BY stage_order;
```

Related Tables for Multi-Stage Auditions:
- candidate_stage_progress — Tracks candidate progression per stage
- candidate_stage_scores — Per-stage aggregated scores
- audition_scaffolds — Has optional project_stage_id FK
- candidate_answers — Has optional project_stage_id FK
