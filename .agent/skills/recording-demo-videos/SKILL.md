---
name: recording-demo-videos
description: Use when you need silent product-demo videos of a real web app without paid tools, manual screen-recording, or a human — scripts a browser through a feature and renders an mp4. Triggers on "demo video", "feature demo", "record the app", "show this feature", "make a walkthrough", or producing many feature demos at once. For Vite/React/Supabase apps (the VettedAI + Congrats stack); the engine is framework-agnostic.
version: 1.0.0
license: MIT
---

# Recording Demo Videos (free, scripted)

Make silent product-demo videos of the **real app** by scripting a browser, then rendering an mp4.
Free and local: **Playwright** drives the app, **ffmpeg** makes the video. No paid SaaS, no narration,
no human clicking. Same script doubles as a UX smoke test, and re-renders when the UI changes — which is
what makes it the sustainable way to produce *many* feature demos.

## When to use

- The user wants one or many feature-demo / walkthrough videos and doesn't want to pay for a tool.
- The recurring "someone has to screen-record every new feature" problem.
- Quick visual proof a feature works, end to end, in the real UI.

Not for: heavily-animated marketing videos with voiceover (use a real editor), or anything needing
a human reacting on camera.

## The shape

```
mint a login session  →  drive the app with Playwright (records .webm)  →  ffmpeg → .mp4
```

Three files land in the target repo under `demo/` (copy from `resources/`):
- `record.mjs` — the engine. A CONFIG block (repo-specific) + a FLOWS map (one entry per video).
- `polish.sh` — `.webm` → `.mp4`, trims the login lead-in, optional burned caption.
- `run.sh` — one command: point dev at staging, record, polish, clean up.
- `README.md` — per-repo usage.

To make a new video: copy a FLOWS entry, change the `url` + `steps`. That's the whole loop.

## Setup checklist (do this once per repo)

1. **Install tooling** (once): `npm install -D @playwright/test && npx playwright install chromium`. Need `ffmpeg` (Homebrew). For *burned captions* you need an ffmpeg built with `libfreetype`; otherwise captions auto-skip and everything else works.
2. **Discover the repo's specifics** and fill the CONFIG block in `record.mjs`:
   - **Dev command** — how the app runs locally (`npm run dev`, often in a subdir like `congrats/`).
   - **Supabase client module path** — usually `src/integrations/supabase/client.ts`. The recorder imports it in-page to log in (see Gotcha 1).
   - **Which DB to record against** — use **staging**, never prod (no real-user PII). Find its URL + anon/publishable key + service key + a direct DB URL. In this org they're in the audition repo's `.env.local` (`VETTED_SUPABASE_*` for VettedAI staging, `STAGING_CONGRATS_SUPABASE_*` for Congrats staging).
   - **A login email** — a synthetic/test account that owns demo-able data. **Always ask the user which account** before minting a session (project rule: no real-user testing without permission).
   - **Routes** — the deep-link paths for the flows you'll record.
3. **Point the local dev server at staging** (see Gotcha 2).
4. **Author a flow**, run `bash demo/run.sh <flow>`, verify by extracting frames (Gotcha 8).

## Gotchas (the hard-won ones — read before debugging)

### 1. Log in via the app's OWN client, not by faking localStorage
Supabase-js writes its session under a non-default key/envelope in the browser; hand-injecting
`localStorage['sb-<ref>-auth-token'] = JSON.stringify(session)` looks right but the client won't read it →
the app bounces to `/login`. Instead: mint a session server-side (admin `generateLink` → `verifyOtp` gives
`access_token`+`refresh_token`, no password needed), then **in the page** `import` the app's supabase client
and call `supabase.auth.setSession({access_token, refresh_token})`. It writes the correct storage and the
session survives navigation. This is the single most important step.

### 2. `--mode staging` may be silently ignored → use `.env.development.local`
`vite-react-ssg dev` (and some setups) ignore `--mode` for env-file loading, so `.env.staging` never loads and
the app stays pointed at prod (you'll see requests to the prod Supabase host). Vite **always** auto-loads
`.env.development.local` in dev at higher priority than `.env`/`.env.local`. So `run.sh` copies your staging
config into `.env.development.local` for the recording, then **deletes it on exit** (otherwise every future
`npm run dev` is silently on staging — a real footgun). Plain `vite` repos may honor `--mode`; test by watching
which Supabase host the app calls.

### 3. Staging schema can lag the frontend → targeted additive reconcile
A staging branch may be missing recent columns the frontend selects → the data query 400s
(`column X does not exist`) and the screen renders empty. Don't replay migrations. Diff the **columns** of the
few tables the screen reads (staging vs prod via `information_schema.columns`), and apply just the missing ones
as **additive, nullable** `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. Get the user's OK — it's a staging DB change.

### 4. Seed data can be on the wrong scale
Synthetic seed scores/values may not match what the UI formatter expects (e.g. scores stored 0–100 while the
UI does `value/5*100` → "1392%"). Check the formatter's expected range against prod's real values; rescale the
seed data if needed (ask first — it's a data mutation).

### 5. Playwright videos don't show the mouse cursor
Inject a fake cursor overlay via `addInitScript` (a dot that follows mousemove + grows on mousedown).
The template already does this. Move the mouse to real coordinates before clicking so it tracks.

### 6. ffmpeg may lack `drawtext`
Builds without libfreetype error on burned captions. `polish.sh` detects `drawtext` and skips the caption if
missing — don't let a caption failure block the mp4.

### 7. Auto-trim the login/boot lead-in
The recording captures the login + app boot (dead seconds). `record.mjs` measures the lead-in and writes a
`.trim` sidecar; `polish.sh` cuts it (`ffmpeg -ss`).

### 8. Verify by frames, never by "it recorded"
`ffmpeg -ss <t> -i out.mp4 -frames:v 1 frame.png` at a few timestamps and actually look. The first runs
will land on `/login`, a skeleton, or the wrong tab — frames are how you catch it.

### 9. Data + auth safety
Record on **staging** with **synthetic** data (e.g. `seed_…@test.vetted.com`), never a real customer's project
(PII). Always ask the user which account to log in as. Minting an auth session is a real action — confirm first.

## Authoring a flow

In `record.mjs`, `FLOWS` is a map of `{ label, url, steps(page, ui) }`. The `ui` helpers cover most needs:
- `ui.settle(what, [words])` — wait for content (networkidle + a word that proves the screen loaded)
- `ui.scrollThrough(fraction, steps)` — smooth scroll down and back
- `ui.clickFirstCandidate()` / generalize to `ui.clickFirst(selectors)` — best-effort click, never hard-fails
- `ui.beat(ms)` — a deliberate pause so the video reads well

Keep flows selector-light and best-effort (try/catch clicks) so a missed selector degrades to "still a fine
scroll demo" instead of a crash. Pace generously (800–1800ms beats); a good silent demo is 15–35s.

## Output + handoff

mp4 lands in `demo/output/` (gitignore it). `open demo/output/<flow>.mp4` to play it (a relative markdown link
won't play in an IDE — it opens the file in the editor). Share the path or `open` it for the user.

## Propagating this skill (it lives in skill-master)

This skill is canonical in `submodules/skill-master/.agent/skills/recording-demo-videos/` and symlinked into each
repo's `.agent/skills/`. After editing it, commit+push the submodule **first**, then the parent repo pointer, and
run `/distribute-skill` to bump it across the sibling repos (ask the user before pushing). See
`skill-master-submodule-sync` rule.
