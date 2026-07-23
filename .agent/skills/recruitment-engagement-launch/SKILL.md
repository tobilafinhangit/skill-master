---
name: recruitment-engagement-launch
description: "Use when an inbound client sends a JD, urgent hiring request, or asks VettedAI/VFA to source candidates, and Codex must convert it into a protected recruitment engagement: opportunity read, fee/deposit terms, calibration questions, client reply, contract fields, invoice memo, and launch handoff."
license: MIT
---

# Recruitment Engagement Launch

Turn a client hiring ask into a protected, launch-ready recruitment engagement. Use this before sourcing begins, especially when urgency could pull VettedAI into unpaid agency work.

## Core Rule

Do not source until the commercial gate is explicit. For urgent searches, optimize for speed and written confirmation: calibrated scope, deposit, candidate ownership, and next step.

## Workflow

### 1. Classify The Ask

Read the client email, JD, call notes, and any prior prospect context. Decide the engagement track:

- **Product pilot:** client should run the role on VettedAI themselves.
- **Done-for-you search:** VettedAI sources/screens/shortlists candidates.
- **Hybrid:** done-for-you search now, product adoption path later.

Default to done-for-you when the client asks for candidates, the role is specialist/senior, or the timeline is urgent.

### 2. Diagnose The Role

Translate the JD into the real hiring problem:

- real role category vs advertised title;
- level and scarcity;
- must-haves, strong pluses, and likely false positives;
- comp/location/timeline realism;
- candidate pool hypotheses;
- risks that need client calibration.

Name title/scope mismatches plainly. Example: "Senior Group Accountant" may really be "Group Accounting / Consolidation / Treasury Lead."

### 3. Choose The Commercial Gate

Use the current VettedAI default unless the user gives a different contract:

- Placement fee: **10% of first-year gross salary** for senior/specialist search.
- Deposit: **30% of the estimated placement fee before sourcing begins**.
- Balance: remaining fee on successful hire, reconciled against accepted compensation.
- Candidate ownership: candidates introduced by VettedAI remain protected for this role/process; use the contract's ownership period when known.
- Contracting: email confirmation can start the admin flow, but deposit/terms must be confirmed before active sourcing.

If the client is strategic and speed matters, recommend "email-confirm terms now, contract/signing in parallel." Do not present "payable only on successful hire" unless the user explicitly waives the deposit.

### 4. Produce The Tactical Reply

Draft a concise client email with:

- acknowledgement and role read;
- done-for-you recommendation;
- commercial terms and deposit;
- first-shortlist target, not guaranteed hire date;
- calibration call request;
- 5-7 must-answer questions;
- explicit "confirm by reply and we will begin" line.

Keep the tone warm, firm, and operational. Avoid sounding like procurement is being dragged in too early.

### 5. Produce The Launch Checklist

After the reply, list what is needed to launch:

- client legal name;
- billing contact and invoice currency;
- signatory name/email/title;
- role title, location, salary range, and final fee estimate;
- deposit amount;
- candidate ownership period and replacement guarantee, if applicable;
- interview process and decision-maker;
- existing candidates already in their pipeline;
- VettedAI role/application link requirement.

Mark fields as `known`, `assumed`, or `missing`.

### 6. Produce The Invoice Memo

Give finance-ready wording:

```
Recruitment deposit for [Client] [Role] search. Placement fee is [X]% of the successful candidate's first-year gross compensation; this invoice covers a [Y]% deposit based on the agreed estimated compensation range of [range]. Final fees will be reconciled against the candidate's accepted offer compensation once confirmed.
```

Include the math:

```
Estimated annual gross = monthly gross x 12
Estimated placement fee = annual gross x fee %
Deposit = estimated placement fee x deposit %
```

When the range is broad, recommend using either the top end or an agreed working figure for the deposit.

### 7. Hand Off To Delivery

If the client confirms terms, invoke or recommend `hiring-role-delivery-pack` next to create the internal role brief, sourcing strategy, outreach copy, audition design, scoring rubric, shortlist template, and working doc.

## Output Shape

Use this order:

```markdown
## Read
<opportunity assessment and recommended track>

## Risks
<commercial, role, timeline, comp, and process risks>

## Recommended Terms
<fee, deposit, balance, ownership, contract path>

## Client Reply
<sendable email>

## Launch Checklist
| Field | Status | Value / Question |
|---|---|---|

## Invoice Memo
<finance-ready text and math>

## Delivery Handoff
<next artifacts to create if confirmed>
```

## Guardrails

- Do not promise final hire by the client's deadline. Promise first shortlist or search momentum.
- Do not let product-free language erase service fees.
- Do not bury the deposit.
- Do not overproduce a full recruiter pack before the client has accepted terms, unless the user explicitly asks.
- If contract terms conflict across prior examples, state the conflict and use the current standard only with user confirmation.
