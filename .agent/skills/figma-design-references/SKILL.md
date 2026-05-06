---
name: figma-design-references
description: Use when a user shares a Figma file URL and wants every (or several) frame translated to static HTML/CSS design references under docs/design-references/. Produces browser-openable specs with per-folder READMEs and a design-system translation guide so engineers don't copy reference CSS into production. Triggers on keywords like "figma", "design references", "translate the designs", or any figma.com/design URL with multiple frames.
version: 1.0.0
license: MIT
---

# Figma → Design References

Translate Figma frames into static HTML/CSS reference files under `docs/design-references/<slug>/` so designers, PMs, and engineers can render them in a browser without a build step. The output is a *visual spec*, not production code — engineers re-implement using the project's existing design system.

## When to use

- User shares a `figma.com/design/...` URL and asks for "design references" or "translate the design"
- User has an existing `docs/design-references/` folder and wants to add more frames
- User asks for a one-time visual reference (no build step, no React, no Tailwind)
- User says something like "do this for all the nodes in this Figma file"

**Don't use for:** writing production React components from a Figma file (use `get_design_context` directly for that), email templates that ship to users (use the canonical email wrapper), one-off screenshots (use `get_screenshot` directly).

## Inputs

- **Figma URL** — required. Parse `fileKey` and optional `nodeId` per the Figma MCP URL parsing rules (convert `-` to `:` in nodeIds).
- **Output root** — defaults to `docs/design-references/`. Create if missing.
- **Slug override** — optional; if user names a slug use it, otherwise derive from the frame name.

## Workflow

### 1. Enumerate the frames
- If the URL has a specific `node-id`, that's the single target.
- Otherwise call `get_metadata` on the file to list top-level frames. Filter to the ones that are page-sized (not icons, not components inside a library). Confirm the list with the user before processing more than ~3 frames.

Show the planned frame list as a short checklist before doing the work.

### 2. For each frame
Run these calls in parallel where possible:
- `get_design_context` with the nodeId — returns React+Tailwind enriched with design tokens
- `get_screenshot` — saved as `assets/preview.png` for visual reference

Then translate:
- **Pull layout, typography, spacing, colors** from the design context. The React/Tailwind output is a *reference* for structure — do not paste it verbatim into the HTML file.
- **Output is plain HTML + inline `<style>` block**, no build, no JS framework, no Tailwind. Browser-openable via `open index.html`.
- **Detect brand variant** from the primary hex (see below). Note in the per-folder README.

### 3. Write the files
Per frame, create:

```
docs/design-references/<slug>/
├── index.html      # standalone HTML+CSS, browser-openable
├── README.md       # what it is + brand + figma node link + translation guide
└── assets/         # screenshot, fonts, images referenced by index.html
    └── preview.png
```

Slug = kebab-case derived from the frame name (e.g. "Shared Shortlist — Recruiter View" → `shared-shortlist-recruiter-view`).

### 4. Update the index README
Append rows to `docs/design-references/README.md` table with: folder, what it is, brand, figma node id. Don't rewrite existing rows — just add the new ones.

### 5. Show the user
Summarize: N frames translated, list paths as clickable links, mention `open docs/design-references/<slug>/index.html` to view.

## Brand auto-detection

Inspect the primary color of the frame's hero / nav / CTA region:

| Primary hex | Brand label | Notes |
|---|---|---|
| `#6c47ff` (or close) | VettedAI purple | Maps to project's `--primary` |
| `#ff6b3d` / `#d94a1e` | Recruiters Ring orange | Co-branded property |
| Other | Note exact hex + ask user | New brand variant |

If the file has multiple brand variants across frames (as in `vetted-newsletter`), call that out in the index README.

## Per-folder README template

```markdown
# <Frame name>

Static HTML reference for the **<frame purpose>** translated from Figma `<file-name>` (node `<node-id>`).

Open `index.html` in a browser — no build step.

**Brand:** <VettedAI purple #6c47ff | Recruiters Ring orange #ff6b3d>
**Figma:** [link to specific node URL]
**Translated:** YYYY-MM-DD

## What this is
<One paragraph describing the page/component and its role.>

## Patterns worth reusing
- <e.g. dark sticky nav, hero gradient, founder-note avatar block>

## Production translation
This file is a **visual spec**, not code to copy. When implementing in production:

| Reference uses | Use in production |
|---|---|
| Hardcoded `#6c47ff` etc. | Tailwind `bg-primary` etc. (HSL tokens in `src/index.css`) |
| Hand-rolled `<button>` / `<input>` / `.card` | Shadcn primitives in `src/components/ui/` |
| Inline `<style>` blocks | Tailwind utility classes |
| Hardcoded font-size px values | Tailwind `text-sm` / `text-base` / `text-lg` |
| Ad-hoc `box-shadow` | `shadow-sm` / `shadow-md` |

⛔ Do not copy this CSS into production. ⛔ Do not install a parallel design system.

## Email exception
If this reference is an email layout, see `.claude/rules/email-template-brand-consistency.md` for the canonical wrapper. Email cannot use Tailwind/Shadcn — but brand discipline (purple, never `talent.vettedai.app` in recruiter footers) carries over.
```

Adjust the translation table to match the *target repo's* design system. The table above is calibrated for VettedAI; for other repos check `src/index.css` (or equivalent) for the actual CSS variable names.

## HTML output rules

- Single `index.html` per frame. No external CSS/JS files except images and fonts under `assets/`.
- Use `<style>` in `<head>`; readable indentation; preserve color hex values verbatim from Figma.
- Use system font stack with the Figma font as primary (`font-family: 'Inter', -apple-system, BlinkMacSystemFont, ...`). Don't bundle webfonts unless the design depends on a non-system one.
- Set `max-width` on the body root to match the Figma frame width (e.g. 640px for emails, 1280px for web pages).
- Include a `<meta name="viewport">` tag.
- Add a `<title>` that matches the frame name.

## Anti-patterns to avoid in the skill output

- ⛔ React/JSX in `index.html` — these must be plain HTML
- ⛔ Tailwind classes — references should be standalone, no build step
- ⛔ `<script>` tags or any JS — references are static
- ⛔ Loading webfonts from external CDNs without mentioning it in README — designers may render offline
- ⛔ Translating production-system patterns "loosely" — if the Figma uses an existing component (nav, button), preserve its visual fidelity but flag it in the README's "patterns worth reusing" section so the engineer reuses the real component

## Final checklist (run before declaring done)

- [ ] All target frames have a folder under `docs/design-references/<slug>/`
- [ ] Each folder has `index.html` + `README.md` + `assets/preview.png`
- [ ] Each `index.html` opens in a browser without errors
- [ ] Each README has the production translation table calibrated to the target repo
- [ ] Top-level `docs/design-references/README.md` has new rows appended
- [ ] If new brand variant detected, called out in top-level README's "Brand variants" section
- [ ] Output paths shared with user as clickable markdown links
