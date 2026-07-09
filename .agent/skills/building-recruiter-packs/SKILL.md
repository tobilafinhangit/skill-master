---
name: building-recruiter-packs
description: Use when turning a new role, JD, hiring-manager call, transcript, or role-context dump into a recruiter pack for sourcing, LinkedIn/profile scraping, screening, and Vetted audition design.
version: 1.0.0
license: MIT
---

# Building Recruiter Packs

Use this after role context exists or when a user asks for sourcing help, scraping strategy, recruiter packs, screening rubrics, or Vetted audition design for a hiring search.

This skill turns messy role inputs into an operating pack recruiters can use immediately.

## Core Rule

Do not treat the JD as the role. The recruiter pack should identify the real hiring problem underneath the JD, then turn that into sourcing signals, profile filters, recruiter questions, and proof-of-work assessment.

## Workflow

1. **Gather context**
   - Read the JD, call transcript/notes, prior prep notes, screenshots, candidate profiles, and any existing role working doc.
   - If the role sits in Tobi's wiki, follow `WIKI.md`: run `ls`, read `wiki/index.md`, read relevant pages, and file durable output under `wiki/research/` unless the user asks for scratch-only.
   - If Vetted audition mechanics are needed, use the built-in Vetted pattern in this skill before opening the product repo. Only inspect the repo if the user needs implementation-level details.

2. **Extract the role thesis**
   - Why this hire exists now.
   - What business/team pain the person reduces.
   - What the first 30-90 days must prove.
   - Who owns the bar and who must trust this person.
   - Which JD keywords are true signals versus noise.

3. **Define the sourceable archetype**
   - Translate the thesis into likely titles, adjacent titles, target company pools, location constraints, and must-have evidence.
   - Name false positives: backgrounds that look right but fail the actual role.

4. **Build the sourcing/scraping layer**
   - Include Boolean strings, title filters, company pools, location strategy, include/exclude keywords, and profile fields to scrape.
   - Add a first-pass scoring rubric that a sourcer can apply from LinkedIn/profile data.

5. **Build recruiter screening**
   - Write 5-8 recruiter-screen questions that separate real ownership from keyword familiarity.
   - Tell the recruiter what strong, weak, and risky answers sound like.

6. **Design the Vetted audition**
   - Split experience verification from work simulation.
   - Experience audition asks what the person actually owned in the past.
   - Skills audition asks how they would reason through realistic work in this role.
   - Include role DNA inputs, dimensions/weights, questions, and score anchors.

7. **Produce the pack**
   - Use the structure in `references/recruiter-pack-template.md`.
   - Keep it operational: searches, fields, rubrics, templates, and next steps.
   - If saved in the wiki, update `wiki/index.md` and `wiki/log.md` after taking a safety snapshot.

## Vetted Audition Pattern

Use this pattern without re-reading the Vetted repo:

- **Experience Audition:** verifies whether the candidate genuinely earned relevant experience. Questions are past-tense, evidence-requesting, and hard to fake. Score dimensions: Complexity & Scope, Ownership & Impact, Context Relevance, Adaptability & Novelty, Reflective Sense-Making, Collaborative Complexity.
- **Skills Audition:** tests present-day judgment through realistic work simulations. It should avoid trivia and generic tests. Score dimensions normally include cognitive/systems reasoning, execution, communication/collaboration, adaptability/learning, judgment/ethics, and emotional intelligence where relevant.
- Strong answers need specific numbers, named decisions, personal attribution, constraints, consequences, mistakes, and reflection. Polished but generic answers cap at the midpoint.

For senior roles, weight ownership, complexity, context relevance, and judgment more heavily than polish.

## Output Checklist

The recruiter pack should normally include:

- Role/search thesis
- Candidate archetype
- Search filters and titles
- Target company pools
- Boolean searches
- Scraping fields
- First-pass profile scoring rubric
- Recruiter screen questions
- Red flags and false positives
- Outreach positioning
- Vetted role DNA
- Experience audition questions
- Skills/work-simulation questions
- Scoring rubric
- Shortlist template
- Open questions / operating notes

## Reference

Open `references/recruiter-pack-template.md` when writing the actual pack.
