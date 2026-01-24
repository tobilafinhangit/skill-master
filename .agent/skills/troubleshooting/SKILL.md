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

### Phase 5: Experiment & Fix
**Goal**: Validate hypothesis and implement the cure.
- **Test the Hypothesis**: Add a log or a check to confirm your suspicion *before* fixing it.
- **Implement the Fix**: Fix the root cause, not just the symptom. Avoid "band-aid" null checks if the data should exist.
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
