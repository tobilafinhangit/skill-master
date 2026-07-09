# Recruiter Pack Template

Use this as a flexible structure. Delete sections that do not apply; keep the operational spine.

## Frontmatter

```yaml
---
title: "[Company] [Role] Recruiter Pack"
type: research
status: active
updated: YYYY-MM-DD
tags: [recruitment, sourcing, audition]
---
```

## Purpose

State what this pack operationalizes:

- JD / role doc
- HM call / transcript
- screenshots or extra context
- candidate profiles if used for calibration
- prior searches or analogous role workflows

## Search Thesis

Plain English:

```text
[Company] is not simply hiring a "[title]." They need [archetype] who can [main ownership], reduce [pain/bottleneck], and succeed in [environment/constraints].
```

Optimize for 4-7 ranked signals. Example signal types:

- production ownership
- commercial ownership
- customer empathy
- regulated-domain judgment
- senior stakeholder management
- speed of execution
- analytical depth
- team leverage
- taste / craft
- ambiguity tolerance

Call out what is nice-to-have but not a hard filter.

## Candidate Archetype

Best-fit profiles usually look like:

- [Title/archetype 1]
- [Title/archetype 2]
- [Adjacent title]
- [Non-obvious but strong background]

The strongest candidates can credibly say:

- "I owned..."
- "I decided..."
- "I changed..."
- "I was trusted with..."
- "The measurable outcome was..."

## Search Filters

### Include Titles

- [Primary title]
- [Adjacent title]
- [Senior/lead variants]
- [Domain-specific variants]

### Be Careful With

- [Title/background that may be a false positive]
- [Consultant/advisor/support variant]
- [Manager-only variant]

### Exclude Or Deprioritize

- [Support-only / junior / unrelated titles]
- [Keyword-heavy profiles with no ownership]
- [Profiles too far from hands-on work, if relevant]

## Target Company Pools

Rank company pools by likely signal quality.

### Tier 1: Closest Domain / Scale Match

List companies or ecosystems where candidates likely faced the same problem shape.

### Tier 2: Strong Adjacent Environments

List non-obvious companies where the underlying operating environment is similar.

### Tier 3: Specialist Backgrounds

Use when a specific technical, regulatory, market, or functional skill matters.

### Tier 4: Conditional Pools

Include only if profiles show the missing ingredient. Example: consulting is useful only with accountable delivery; management is useful only with recent hands-on execution.

## Boolean Searches

Create 3-5 strings:

### Core Search

```text
("[primary title]" OR "[adjacent title]" OR "[alternate title]")
AND ([must-have keyword 1] OR [must-have keyword 2])
AND ([ownership/signal keyword 1] OR [ownership/signal keyword 2])
```

### Domain Variant

```text
("[title]" OR "[title]")
AND ([domain keyword] OR [regulated/industry keyword])
AND ([impact keyword] OR [scale keyword])
```

### Seniority / Ownership Variant

```text
("[senior title]" OR "[lead title]")
AND ("owned" OR "led" OR "built" OR "scaled" OR "reviewed" OR "on-call" OR "P&L" OR "pipeline")
AND ([must-have skill/context])
```

### Exclusion Terms

```text
NOT ([support-only keyword] OR [junior keyword] OR [unrelated keyword])
```

Use exclusions lightly. Strong candidates can have older irrelevant roles before later owning the right work.

## Scraping Fields

Use a table like this:

| Field | Why it matters |
|---|---|
| Name | Basic identity |
| LinkedIn URL | Source of truth |
| Current title/company/location | Current fit |
| Previous relevant companies | Domain/scale inference |
| Years in relevant function | Seniority proxy |
| Current hands-on status | Detect manager-only false positives |
| Must-have skill evidence | Core JD/context requirement |
| Ownership phrases | Main selection signal |
| Scale markers | Users, revenue, transactions, team size, geography, uptime, budget |
| Stakeholder/team evidence | Collaboration and trust proxy |
| Domain evidence | Plus or requirement depending on role |
| Red flags | Reason for deprioritization |
| Search query/source | Sourcing audit trail |
| Recruiter notes | Why advance or reject |

## First-Pass Scoring

Score from profile data before outreach or audition.

| Dimension | Weight | What 5 Looks Like |
|---|---:|---|
| [Main ownership signal] | 25% | [Concrete evidence] |
| [Seniority / judgment] | 20% | [Concrete evidence] |
| [Domain or technical depth] | 20% | [Concrete evidence] |
| [Breadth / collaboration] | 15% | [Concrete evidence] |
| [Context relevance] | 10% | [Concrete evidence] |
| [Learning / communication / taste] | 10% | [Concrete evidence] |

Recommended thresholds:

- 4.0+ weighted score: strong prospect.
- 3.3-3.9: maybe; proceed if one standout signal exists.
- Below 3.3: deprioritize unless market is thin.

Hard stop risks:

- no evidence of the primary ownership signal
- missing a true must-have
- title inflation without concrete outcomes
- too far from the day-to-day work

## Recruiter Screen Focus

Ask questions that force ownership, context, and specificity:

1. What have you personally owned that is closest to this role?
2. What decision did you make that changed the outcome?
3. What broke, stalled, or failed, and what did you do?
4. What did others rely on you for?
5. What did you have to learn quickly?
6. How hands-on are you today?

Listen for:

- systems, numbers, timelines, stakeholders, constraints
- "I decided / I owned / I changed" language
- honest limitations and learning loops
- clear trade-offs

Be wary of:

- "we" with no personal attribution
- generic process answers
- long tool lists without consequences
- confidence without depth when probed

## Outreach Positioning

Lead with the real hook, not the job title.

```text
Hi {{first_name}},

I am working with {{company}} on a {{role}} search. This is for someone who has genuinely owned {{main problem/area}}, not just {{false-positive activity}}.

What stood out in your profile was {{specific_signal}}. The team is especially interested in people who can {{top success signal 1}}, {{top success signal 2}}, and {{top success signal 3}}.

Would you be open to a short conversation this week?
```

## Vetted Audition Design

### Role DNA Inputs

| Field | Input |
|---|---|
| Goals | [What this hire must improve or unlock] |
| Stakeholders | [Hiring manager, team, cross-functional partners, customers] |
| Decision horizon | [What 30-90 day success proves] |
| Tools | [Tools, systems, channels, methods, domain artifacts] |
| KPIs | [How success is measured] |
| Constraints | [Time, regulation, ambiguity, team bandwidth, market constraints] |
| Cognitive type | [Systems reasoning, commercial judgment, taste, analytical depth, etc.] |
| Team topology | [How the team is structured and where the role sits] |
| Cultural tone | [Ownership style and working norms that matter] |

Context flags:

- Role family:
- Seniority:
- Startup/high-growth context:
- People management:

Clarifier inputs:

- Ambiguity:
- Time pressure:
- Cross-functional:
- Customer-facing:
- Regulated:
- Analytical-data-heavy:

### Experience Audition

Use 5 questions for a shorter senior audit; 10 if the search is high stakes and the candidate pool is broad.

Dimensions:

- Complexity & Scope
- Ownership & Impact
- Context Relevance
- Adaptability & Novelty
- Reflective Sense-Making
- Collaborative Complexity

Question pattern:

```text
Describe [specific past situation] you personally owned. Share [scale markers], [decision/trade-off], [what went wrong or was hard], and [outcome/reflection].
```

Avoid:

- "Tell me about a time..."
- purely hypothetical questions
- questions that reward polished philosophy without evidence

Good questions ask for:

- numbers
- timeline
- systems/processes/accounts
- personal decisions
- consequences
- counterfactuals
- mistakes and learning

### Skills / Work Simulation Audition

Use 4-6 realistic scenarios from the first 90 days of the role.

Each scenario should test:

- current judgment
- sequencing
- communication
- risk awareness
- assumptions
- trade-offs

Prompt shape:

```text
[Realistic messy situation]. Walk through your first [time window / steps]: [stabilize/diagnose/decide/communicate/execute].
```

Avoid trivia and generic tests unless that is the real work.

### Scoring

Use 0-5 anchors:

| Score | Meaning |
|---:|---|
| 0 | No answer or irrelevant answer |
| 1 | Generic, theoretical, no specifics |
| 2 | Some relevant content but shallow or mostly "we" language |
| 3 | Competent and plausible, but not clearly high-trust |
| 4 | Strong, specific, owned, realistic, role-aware |
| 5 | Exceptional: hard-to-fabricate detail, deep ownership, clear trade-offs, strong learning and team leverage |

Calibration rule: a candidate cannot score 4 or 5 without specific evidence. If the answer sounds good but could apply to almost anyone, cap it at 3.

## Shortlist Template

```text
Candidate:
Current role/company/location:
LinkedIn:
Comp/location/availability:

Why this candidate is in the shortlist:

Strongest evidence:
- Primary ownership signal:
- Role/domain depth:
- Judgment / problem-solving:
- Collaboration / stakeholder trust:
- Learning / adaptability:

Vetted audition summary:
- Experience score:
- Skills score:
- Best answer:
- Main concern:

Interview focus:
1.
2.
3.

Recommendation:
Advance / Hold / Reject
```

## Operating Notes

Include:

- what to show the client during sourcing
- update cadence
- who reviews candidates
- how the Vetted pipeline compares with any client-side pipeline
- what remains unconfirmed
