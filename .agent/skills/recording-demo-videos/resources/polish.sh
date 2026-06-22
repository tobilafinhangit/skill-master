#!/usr/bin/env bash
# Turn a raw Playwright .webm into a shareable .mp4 (free, ffmpeg only).
# Usage: bash demo/polish.sh demo/output/candidate-ranking.webm ["Optional caption"]
# If a "<input>.webm.trim" file exists (written by record.mjs), trims that many
# seconds off the front to drop the login/boot lead-in.
set -euo pipefail

SRC="${1:?usage: polish.sh <input.webm> [caption]}"
CAPTION="${2:-}"
OUT="${SRC%.webm}.mp4"

# Auto-trim lead-in if the recorder left a sidecar
SS=0
[ -f "${SRC}.trim" ] && SS="$(cat "${SRC}.trim")"

# A font that exists on macOS for the optional caption
FONT=""
for f in \
  /System/Library/Fonts/Supplemental/Arial.ttf \
  /System/Library/Fonts/Helvetica.ttc \
  /System/Library/Fonts/SFNS.ttf ; do
  [ -f "$f" ] && FONT="$f" && break
done

# yuv420p + even dims = plays everywhere (Slack, QuickTime, browsers)
VF="scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p"

# drawtext needs an ffmpeg built with libfreetype; skip the caption if unavailable
HAS_DRAWTEXT=0
ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' drawtext ' && HAS_DRAWTEXT=1

if [ -n "$CAPTION" ] && [ -n "$FONT" ] && [ "$HAS_DRAWTEXT" = "1" ]; then
  ESC=$(printf '%s' "$CAPTION" | sed "s/\\\\/\\\\\\\\/g; s/:/\\\\:/g; s/'/\\\\'/g")
  # purple lower-third for the first 4 seconds (note: @0.85 = alpha, not a 'cc' suffix)
  VF="${VF},drawtext=fontfile=${FONT}:text='${ESC}':fontcolor=white:fontsize=28:box=1:boxcolor=0x7C3AED@0.85:boxborderw=16:x=40:y=h-92:enable='lt(t-${SS}\,4)'"
fi

ffmpeg -y -ss "$SS" -i "$SRC" -vf "$VF" -c:v libx264 -preset slow -crf 20 -movflags +faststart -an "$OUT" >/tmp/demo-ffmpeg.log 2>&1 \
  || { echo "ffmpeg failed — tail of log:"; tail -8 /tmp/demo-ffmpeg.log; exit 1; }
echo "✅ mp4: $OUT  ($(du -h "$OUT" | cut -f1), trimmed ${SS}s lead-in)"
