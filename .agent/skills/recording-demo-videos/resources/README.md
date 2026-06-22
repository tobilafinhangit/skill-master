# Demo recorder

Free, scripted product-demo videos of the real app (Playwright drives it, ffmpeg renders mp4).
Generated from the `recording-demo-videos` skill.

## One command
```bash
bash demo/run.sh <flow> ["Optional caption"]
```
Points a local dev server at staging, logs in head-lessly, records the flow, makes the mp4,
and cleans up after itself. Output → `demo/output/<flow>.mp4` (gitignored). Play it: `open demo/output/<flow>.mp4`.

## Add a feature demo
Edit `demo/record.mjs` → copy a `FLOWS` entry → change `url` + `steps`. Helpers: `ui.settle`,
`ui.scrollThrough`, `ui.clickFirst`, `ui.beat`. Keep clicks best-effort; pace 800–1800ms; aim 15–35s.

## Config
The CONFIG block at the top of `record.mjs` holds the repo-specific bits (base URL, staging Supabase
URL, key env-var names, login email, supabase client module path). `demo/.env.staging` (gitignored)
points the dev server at staging. See the `recording-demo-videos` skill for the gotchas.
