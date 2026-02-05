This document enumerates all tables in the public schema, including columns, constraints, RLS policies, enums/types, and functions/triggers references when relevant.

Notes:

Nullability is inferred where "nullable" appears in column options.
Defaults are shown as database expressions.
RLS policies list effective logic (policy names and USING/WITH CHECK).
Custom enum: app_role with values: TALENT, RECRUITER, PARTNER_VIEWER, admin, moderator, user, ops_manager, super_admin.
Helper functions referenced in policies include: has_permission(text), is_admin(), is_super_admin(), check_user_is_admin(uuid), check_user_is_super_admin(uuid), get_user_role(uuid), get_current_user_email(), and auth.* helpers. Their definitions are not listed here but they are required for policy logic.*
Extensions in use that affect schema defaults: extensions.uuid_generate_v4(), gen_random_uuid(), pgcrypto, pg_net, pg_graphql, vault (and others). Edge Functions present but omitted here unless tied to triggers.

Table: audition_submissions
Purpose: Stores user submissions for auditions. opportunity_id stores external bank_id from Vetted (TEXT).

MULTI-STAGE WARNING: A user can have MULTIPLE submissions for the same opportunity_id (different stages like experience/skills). NEVER use .single() when querying by (user_id, opportunity_id) - use .order().limit(1) instead. See: backend/docs/MULTI_STAGE_AUDITION_PATTERNS.md

Columns:

id uuid NOT NULL DEFAULT extensions.uuid_generate_v4()
user_id uuid NOT NULL
opportunity_id text NOT NULL — Vetted bank_id string
questions jsonb NOT NULL
audio_urls jsonb NOT NULL
status text NULL DEFAULT 'pending'::text
submitted_at timestamptz NULL
reviewed_at timestamptz NULL
reviewer_id uuid NULL
duration_seconds int4 NULL
user_agent text NULL
ip_address text NULL
rating int4 NULL CHECK (rating >= 1 AND rating <= 5)
feedback_reason text NULL
feedback_text text NULL
is_test_data bool NULL DEFAULT false
candidate_name text NULL
candidate_email text NULL
vetted_feedback jsonb NULL — structured AI feedback
feedback_received_at timestamptz NULL
exit_reason text NULL — technical, emergency, need_time, other
exit_reason_details text NULL
exit_reason_details text NULL
exited_at timestamptz NULL
exit_question_index int4 NULL
vetted_webhook_sent_at timestamptz NULL
vetted_webhook_error text NULL
updated_at timestamptz NULL DEFAULT now()
expires_at timestamptz NULL
created_at timestamptz NULL DEFAULT now()
event_id text NULL
notified_at timestamptz NULL
resume_url text NULL
project_id uuid NULL — internal link to vetted_projects.id
proctoring_data jsonb NULL
stage_id text NULL
stage_type text NULL DEFAULT 'skills'::text CHECK (stage_type = ANY(ARRAY['experience','skills'])) — experience or skills
stage_order int4 NULL DEFAULT 1 — 1 for experience, 2 for skills
rejection_reason text NULL
rejected_at timestamptz NULL
promoted_at timestamptz NULL
promoted_by text NULL
webhook_retry_count int4 NULL DEFAULT 0
webhook_permanently_failed bool NULL DEFAULT false
webhook_failed_reason text NULL
webhook_last_notified_at timestamptz NULL
webhook_last_notified_error text NULL
webhook_acknowledged_at timestamptz NULL
started_at timestamptz NULL
reminder_sent_at timestamptz NULL
Constraints:

PK: id
FKs:
public.job_applications.audition_submission_id → public.audition_submissions.id
public.submission_events.submission_id → public.audition_submissions.id
public.deprecated_proctoring_snapshots.submission_id → public.audition_submissions.id
public.support_messages.submission_id → public.audition_submissions.id
public.client_logs.audition_id → public.audition_submissions.id
public.audition_submissions.project_id → public.vetted_projects.id
RLS: Enabled

"Admins with permission can view all submissions" SELECT: (auth.uid() = user_id) OR has_permission('submissions.view_all')
"Users can view own submissions" SELECT: auth.uid() = user_id
"Users can create own submissions" INSERT WITH CHECK: auth.uid() = user_id
"Users can update own submissions" UPDATE USING: auth.uid() = user_id
"Can update submissions with permission" UPDATE USING: has_permission('submissions.edit')
"Can delete submissions with permission" DELETE USING: has_permission('submissions.delete')
"Admins can manage all submissions" ALL USING/CHECK: check_user_is_admin(auth.uid())
Additional admin SELECT policy variant also present via authenticated role.
Enums & Types: uses app_role via policies only.

Functions & Triggers: Referenced by submission_events and job_applications via FKs; webhook columns imply external Edge Functions interact but triggers not listed here.

Table: audition_answers
Purpose: Stores individual question answers for auditions. Each row is one answer to one question.

MULTI-STAGE NOTE: The stage_type column indicates which stage this answer belongs to. EXP_* question_ids belong to 'experience' stage, other question_ids belong to 'skills' stage.

Columns:

id uuid NOT NULL DEFAULT extensions.uuid_generate_v4()
user_id uuid NOT NULL
opportunity_id text NOT NULL — Vetted bank_id string (matches audition_submissions.opportunity_id)
question_id text NOT NULL — Question identifier (EXP_* for experience, Q* for skills)
question_text text NOT NULL — The question that was asked
audio_url text NOT NULL — Public URL to the audio recording
audio_path text NOT NULL — Storage path in Supabase bucket
transcript text NULL — Transcribed text (populated async by transcription job)
submitted_at timestamptz NULL DEFAULT now()
transcription_status text NULL DEFAULT 'pending' — pending, processing, completed, failed
client_upload_id text NULL — Idempotency key for upload retries
is_practice bool NULL DEFAULT false — True if this is a practice answer
created_at timestamptz NULL DEFAULT now()
stage_type text NULL — 'experience' or 'skills' (inferred from question_id pattern)
answer_type text NULL — 'intro', 'practice', or 'official'

Constraints:

PK: id
Unique: (user_id, opportunity_id, question_id) — One answer per question per user per opportunity
RLS: Enabled

"Users can view own answers" SELECT: auth.uid() = user_id
"Users can create own answers" INSERT WITH CHECK: auth.uid() = user_id
"Users can update own answers" UPDATE USING: auth.uid() = user_id
"Admins can manage all answers" ALL USING/CHECK: check_user_is_admin(auth.uid())

Related Tables:
- audition_submissions — Parent submission record
- transcription_jobs — Async transcription processing

Table: vetted_projects
Purpose: Cached jobs/projects synced from VettedAI.

Columns:

id uuid NOT NULL DEFAULT extensions.uuid_generate_v4()
vetted_project_id uuid NOT NULL UNIQUE
project_title text NOT NULL
recruiter_email text NOT NULL
recruiter_name text NULL
audition_url text NOT NULL
status text NULL DEFAULT 'active'::text
created_at timestamptz NULL DEFAULT now()
updated_at timestamptz NULL DEFAULT now()
total_submissions int4 NULL DEFAULT 0
last_submission_at timestamptz NULL
role_title text NULL
company_name text NULL
location text NULL
employment_type text NULL
access_mode text NULL
project_status text NULL
candidate_facing_jd jsonb NULL
synced_at timestamptz NULL
is_confidential bool NULL DEFAULT false
is_demo bool NULL DEFAULT false
job_visibility bool NULL DEFAULT false
job_accessibility bool NULL DEFAULT false
audition_visibility bool NULL DEFAULT false
audition_accessibility bool NULL DEFAULT false
default_window_hours int4 NULL DEFAULT 36
default_duration_minutes int4 NULL DEFAULT 60
default_extension_hours int4 NULL DEFAULT 24
stages jsonb NULL
Constraints:

PK: id
FKs from other tables:
notifications.job_id → vetted_projects.vetted_project_id
audition_submissions.project_id → vetted_projects.id
RLS: Enabled

"Anyone can view active projects" SELECT: status = 'active'
"Public can view visible projects" SELECT (anon, authenticated): job_visibility = true
"Public read vetted projects" SELECT: true
"Admins with permission can view all projects" SELECT: (status = 'active') OR has_permission('projects.view_all')
"Recruiters can view own projects" SELECT: recruiter_email = (auth.jwt()->>'email')
"Can update projects with permission" UPDATE USING: has_permission('projects.edit')
"Can delete projects with permission" DELETE USING: has_permission('projects.delete')
"Admins can manage vetted projects" ALL USING/CHECK: check_user_is_admin(auth.uid())
