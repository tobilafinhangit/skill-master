---
name: annotating-html-mockups
description: Use when the user asks to mockup a flow, screen, or feature design before implementation, or wants an HTML mockup they can annotate with element-level feedback. Produces a self-contained HTML mockup with click-to-annotate #n chips, and a parseable export the agent reads back to align on design before coding.
version: 1.0.0
---

# Annotatable HTML Mockups

Turn a "let's align on the design before you build" request into a **browser-openable HTML mockup that the user annotates element-by-element**, exports their feedback, and the agent reads back verbatim. The loop: **mockup → annotate → export → align → build**.

## When to use

- User asks to *mockup* a flow/feature before implementation, or says "let's talk design first", "let me look at the screens first".
- The design has open questions (placement, visibility, copy) the user should weigh in on per-element.
- The user is a non-engineer: feedback must not require reading code — they click elements and type notes.
- Alignment before code was the explicit request ("once we're aligned we can proceed").

Do NOT use for: shipping production UI (use the real design system), Figma-frame translation (see `figma-design-references`), or when the user just wants a quick sketch in chat text.

## Deliverable

One self-contained HTML file (no build step, no external deps) under `docs/design-references/<slug>/index.html`, plus a short `<slug>/README.md` pointing at it. The HTML embeds a **note layer**:

- Every annotatable element carries a `#n` chip.
- Clicking a chip opens a note panel; notes persist in `localStorage` (survive reload).
- An **"Export my feedback"** button downloads a `.txt` with `element-label → note` pairs the agent parses back.
- Chips turn amber once annotated so the user sees what still needs their eyes.

## Workflow

1. **Clarify the shape.** Ask (or infer from the request) *which screens/frames* the flow needs — rarely more than 3–4. Group them as frames in one page (vertical, scrollable) with clear "Frame N" headers rather than a multi-file mockup.
2. **Build from the starter template** (`templates/mockup-template.html`). Copy it, rename to `index.html` under `docs/design-references/<slug>/`, then:
   - Swap in the product chrome (product bar, tabs, role/context names) to match the repo.
   - Replace the frame bodies with your mockup of the target flow — use the repo's design tokens (colors, radius, font) not invented ones. See the repo's `docs/design-references/README.md` for the "reference vs production" translation rules.
   - Assign a `data-note="kebab-key"` chip per **decision-worthy** element. Give LABELS a human name for every key.
   - Preserve the annotation JS verbatim (it's the load-bearing part).
3. **Open/open point the file.** Give the user the path in the chat — "double-click `docs/design-references/<slug>/index.html`". No instructions beyond "click a # chip, type, save".
4. **Surface the open questions.** In a closing "Open questions" note on the page, enumerate the decisions you want the user to rule on — explicitly invite annotation there.
5. **Wait for the export.** The user pastes the `.txt` back (or says done). **Parse it faithfully**: read each `element → note`, treat every note as authoritative feedback, do not editorialize or drop notes. Map them to concrete changes.
6. **Align, then build.** Summarize the agreed design back in one short paragraph, confirm, and only then write code (in a worktree per the repo's branch policy).

## Export format (the parse contract)

The generated `.txt` looks like:

```
VettedAI — Sourcing UX mockup annotations
====================================================

1) Frame 1 · "Recent pack runs" heading + cards
   → move these below the pack chooser, cap at 3

2) Frame 2 · Row: strong match, no email
   → add a per-row Find email here

— export from 2026-08-23
```

When the user pastes this, parse each `N) <label>` + `→ <note>`. If a note is ambiguous, ask ONE clarifying question per ambiguous note — never guess a design decision. Never discard a note as "minor".

## Design tokens (use the repo's, don't invent)

Reuse what the repo's `docs/design-references/README.md` documents (e.g. VettedAI purple `#6c47ff` ≈ `#6558d8`, 12px radius, Inter). The annotation layer CSS is dark-neutral and works with any palette — keep it as-is.

## Starter template

Full working annotation layer + one empty frame + the export button: `templates/mockup-template.html`. Copy it as the base; the sourcing-UX example live in this repo is `docs/design-references/sourcing-ux-fixes/index.html` (reference implementation, not the template).

## Checklist

- [ ] Frames ≤ ~4, one per screen moment
- [ ] Every decision-worthy element has a `data-note` chip + a LABELS entry
- [ ] Annotation JS copied verbatim (localStorage + export + amber-done)
- [ ] Open-questions block at the bottom
- [ ] User told how to open + export; export parsed back faithfully before any code
- [ ] README.md beside the mockup