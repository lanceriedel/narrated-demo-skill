#!/usr/bin/env bash
# Record the screen while a command performs the action.   record_screen.sh <scene-dir> <seconds> -- <command…>
# Writes <scene-dir>/page.mov and marks.json {started: ms} — `started` is set when the command prints a line containing MARK
# (or at command start if it never does). Use the dir as `video:` in the scene spec.
# Gotcha: `screencapture -V` only advances when pixels change — a static terminal freezes the recording. Keep something ticking on screen
# (see show_file.sh) or make sure the command produces visible output throughout.
set -uo pipefail
D=$1; SECS=$2; shift 2; [ "${1:-}" = "--" ] && shift
mkdir -p "$D"; rm -f "$D"/page.mov "$D"/marks.json; sleep 2
screencapture -x -V "$SECS" "$D/page.mov" & CAP=$!; T0=$(python3 -c 'import time;print(time.time())'); sleep 1.5
started=""
"$@" 2>&1 | while IFS= read -r line; do
  echo "$line"
  if [ -z "$started" ] && [[ "$line" == *MARK* ]]; then started=1; python3 -c "import time,json;print(json.dumps({'started':int((time.time()-$T0)*1000)}))" > "$D/marks.json"; fi
done
[ -f "$D/marks.json" ] || echo '{"started": 0}' > "$D/marks.json"
i=0; while kill -0 $CAP 2>/dev/null && [ $i -lt $((SECS+15)) ]; do sleep 1; i=$((i+1)); done
kill -0 $CAP 2>/dev/null && { echo "capture overran; killing"; kill $CAP; }
echo "→ $D/page.mov ($(stat -f %z "$D/page.mov" 2>/dev/null) bytes), marks $(cat "$D/marks.json")"
