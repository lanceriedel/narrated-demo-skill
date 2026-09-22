#!/usr/bin/env bash
# Check/install what the renderer needs. Safe to re-run.
set -uo pipefail
S=$(cd "$(dirname "$0")/.." && pwd)
ok(){ printf '  \033[32m✓\033[0m %s\n' "$1"; }; miss(){ printf '  \033[31m✗\033[0m %s\n' "$1"; }
command -v ffmpeg >/dev/null && ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')" || miss "ffmpeg — brew install ffmpeg"
command -v node >/dev/null && ok "node $(node -v)" || miss "node — brew install node"
command -v screencapture >/dev/null && ok "screencapture (macOS)" || miss "screencapture — screen scenes need macOS"
[ -n "${TTS_API_KEY:-}${OPENAI_API_KEY:-}" ] && ok "TTS key present" || miss "TTS key — export OPENAI_API_KEY, or TTS_API_KEY + TTS_URL=https://<proxy>/v1/audio/speech"
PW=${PW_REPO:-$S/pw}
if [ -d "$PW/node_modules/@playwright/test" ]; then ok "Playwright at $PW"; else
  echo "  installing Playwright into $PW (one-time, ~2 min)…"; mkdir -p "$PW"; cd "$PW"
  [ -f package.json ] || echo '{"name":"narrated-demo-pw","private":true,"type":"module"}' > package.json
  npm i -s @playwright/test >/dev/null 2>&1 && npx playwright install chromium >/dev/null 2>&1 && ok "Playwright installed at $PW" || miss "Playwright install failed — cd $PW && npm i @playwright/test && npx playwright install chromium"
fi
[ -f ~/.config/slack-mcp/credentials.json ] && ok "Slack credentials (slack-mcp) for slack_post.py" || echo "  · no ~/.config/slack-mcp/credentials.json — slack_post.py unavailable; hand the .mov to the user"
