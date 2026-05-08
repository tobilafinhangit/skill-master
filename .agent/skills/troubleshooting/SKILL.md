---
name: troubleshooting
description: Inspects, diagnoses, and resolves application issues using a systematic, hypothesis-driven approach. Use when the user asks to fix a bug, debug an error, or troubleshoot a system.
---

# Troubleshooting

A systematic, scientific approach to debugging complex software issues. This process mirrors the rigorous standards of high-performing engineering teams (e.g., Google, Stripe).

## When to Use This Skill
- User reports a "bug", "error", "crash", or "unexpected behavior".
- You encounter an error during the execution of another task.
- You need to investigate a complex system failure.
- The user asks "why is this happening?" or "how do I fix this?".

## Core Philosophy: The Scientific Method
Debuging is not guessing. It is the process of forming hypotheses and testing them until the truth is revealed.
1. **Observe**: Gather data (logs, traces, reproduction).
2. **Hypothesize**: Formulate a theory for *why* it's broken.
3. **Test**: Prove or disprove the theory.
4. **Fix**: Implement the solution.
5. **Verify**: Prove the fix works and breaks nothing else.

## Process

### Phase 1: Stop & Assess
**Goal**: Understand the scope and context before touching code.
- **Don't Panic**: Resist the urge to randomly change code.
- **Check Recent Changes**: What changed recently? (Commits, deploys, env vars).
- **Check Environment**: Is this happening on Prod? Staging? Local?
- **Search Existing Issues**: Has this been reported before?

### Phase 2: Reproduce
**Goal**: Create a minimal, deterministic reproduction case.
- **Isolate**: Remove variables until you have the smallest possible amount of code that triggers the bug.
- **Automate**: Can you write a failing test case? (See `test-driven-development` skill).
- **Document**: Write down the exact steps to reproduce.

### Phase 3: Observe & Gather Evidence
**Goal**: See the error in high fidelity.
- **Logs**: Read the *entire* stack trace. Look for "Caused by".
- **Binary Search**: Use `git bisect` or divide-and-conquer logging to find the origin.
- **Inspections**: Check database state, API responses, network traffic.

### Phase 4: Hypothesize
**Goal**: Brainstorm potential causes.
- List at least 3 potential root causes.
- Rank them by probability.
- **Ask "Why?" Five Times**: Go deeper than the symptom.
    - *Symptom*: Profile page crashes.
    - *Why?* User object is null.
    - *Why?* API returned 404.
    - *Why?* User ID was undefined in the request.
    - *Why?* LocalStorage was cleared. -> **Root Cause**.

### Phase 4.5: Quantify Blast Radius (Mandatory)
**Goal**: Find every user/record affected, not just the reporter.

Once a root cause is identified — even tentatively — invoke the `impact-analysis` skill to quantify how many other records or users are affected by the same root cause. The reporter is rarely the only one. This step is **mandatory before applying the fix** because it determines whether the work is just a code fix or also requires:
- A backfill (fixing data that's already broken)
- A user notification (telling affected users what happened)
- A different fix shape (a per-record symptom may be platform-wide)

**How to apply:**
1. Run `impact-analysis` against the root cause hypothesis. Pass the failing condition as a SQL or PostgREST filter (e.g., "candidates with `status='scoring'` for >2h", "edge functions sending `Authorization: Bearer` to `/functions/v1/*`").
2. Report `affected_count` to the user explicitly: "Reporter is 1 of N affected — N=…".
3. Decide the fix shape based on `N`:
    - `N == 1` → code fix only, no backfill.
    - `1 < N < 50` → code fix + targeted backfill SQL or repair script. Surface a list to the user.
    - `N >= 50` or any user-facing data integrity / billing impact → code fix + backfill + outbound notification (apology email, in-app banner, Discord ops note). Open a follow-up ticket if the backfill is non-trivial.
4. If the impact query itself errors (Supabase MCP / PostgREST blip), do NOT block the fix — log the failure to the user and proceed with code fix only, but flag it as an explicit unknown.

**Why this is here:** Prior incidents (HoaQ apology — 605 emails, survey-401 — 76 candidates, stranded candidates — 927 affected) all had the same shape: the reporter surfaced one symptom, the agent fixed code, and the broader population was discovered only when the user manually asked "how many people did this affect?" Standardizing this step turns reactive triage into a default safety net.

### Phase 5: Experiment & Fix
**Goal**: Validate hypothesis and implement the cure.
- **Test the Hypothesis**: Add a log or a check to confirm your suspicion *before* fixing it.
- **Implement the Fix**: Fix the root cause, not just the symptom. Avoid "band-aid" null checks if the data should exist.
- **Backfill / Notify** (if Phase 4.5 indicated): apply the data repair and send the notification *before* declaring the work done. A code fix that leaves bad data behind is half a fix.
- **Code Review Self-Check**:
    - Does this introduce a regression?
    - Is this the simplest fix?
    - Does it handle edge cases?

### Phase 6: Verify
**Goal**: Ensure the monster is dead.
- **Run the Reproduction Case**: It should pass now.
- **Run the Suite**: Ensure no regressions.
- **Manual Check**: Verify the user flow end-to-end.

### Phase 7: Root Cause Analysis (RCA) & Prevention
**Goal**: Ensure this specific class of bug never happens again.
- **Add Regression Test**: Leave a permanent sentinel in the codebase.
- **Improve Observability**: Add logs that would have made this easier to find.
- **Documentation**: Update docs if this was a misunderstanding of the system.

## Common Error Patterns & Solutions

| Pattern | Checks |
| :--- | :--- |
| **NullReference / Undefined** | Check data flow, API response shapes, uninitialized state. |
| **Network / Timeout** | Check connectivity, firewall, CORS, correct URLs, service status. |
| **Auth / 401 / 403** | Check tokens, scopes, headers, expiration, RLS policies. |
| **Performance / Hang** | Check infinite loops, deadlocks, missing database indexes, N+1 queries. |
| **Logic Error** | Check conditionals, off-by-one loops, boolean logic. |
| **Database Error** | Check constraints, foreign keys, migrations, connection pool. |

## Tools & Commands
- **Grep**: `grep -r "error_string" .`
- **Find**: `find . -name "*log*"`
- **Git**: `git log -p filename`, `git bisect`
- **Network**: `curl -v url`
- **Database**: Check schema and constraints using `db-schema` skill if available.

## Instructions for Use
1.  **Acknowledge** the issue and ask for any missing context (logs, reproduction steps).
2.  **Follow the phases** above explicitly. Don't skip to "Fix".
3.  **Narrate your investigation** to the user (e.g., "I am checking the logs to see...").
4.  **Propose the fix** and request review before applying complex changes.
