---
name: narrated-demo
description: "Turn what the agent is currently working on into a short narrated demo video (TTS voice-over + screen/browser captures + lower-third captions → one H.264 .mov). Use when the user asks for a demo clip, walkthrough video, narrated recording, or 'make a video of this'. Interviews the user (audience, story, scenes), writes a scene spec, renders it scene by scene, and optionally posts to Slack."
---

# Narrated demo

One agent, one afternoon, one `.mov` that a VP can watch on a phone. The recipe (proven on five clips, 69–188 s each):

1. **Interview** the user — five questions, no more (below). Draft the story *from the context you already have*; the user edits, not writes.
2. **Write a scene spec** (`clips/<name>.yaml`): 4–8 scenes, ~25–45 words of narration each (≈ 10–18 s spoken). Every scene has a **payoff**
   — the moment the thing appears — and the video is cut so the payoff shows early, not last.
3. **Render**: `scripts/render_clip.py clips/<name>.yaml`. Per scene: TTS → capture → fit video to audio → caption → mux; then concat.
4. **Review** the stills the renderer writes (`out/_<clip>_<scene>.png`) with the `read` tool before declaring done. Re-render single scenes with `--only s2`.
5. **Post** (optional): `scripts/slack_post.py <channel_id> out/<clip>.mov "<blurb>"`.

Everything is re-runnable and cached (TTS by text hash, video per scene), so iterating on one sentence costs seconds.

## 1. The interview (ask these, then draft)

Ask all five in one message; accept partial answers and fill the rest from context, labelling what you assumed.

1. **Who is it for, and how long do they have?** (peer engineer 3 min · exec 90 s · Slack scroll 60 s) → sets scene count and pace.
2. **What is the one thing they should believe after watching?** → becomes scene 1's first sentence and the last scene's last sentence.
3. **What must be on screen?** (a UI, a terminal, a document, a chart, a file) → decides capture types. Ask for URLs / commands / paths.
4. **What is the 'live' moment?** Something that visibly *happens* (a query returning, a build finishing, a number appearing). One per clip minimum.
5. **Voice and tone?** Default: `onyx`, "calm, clear, confident tech-demo narration, medium pace, slight emphasis on numbers". Offer `alloy`/`nova` if they want lighter.

Then **propose the storyboard as a table** (scene · what's on screen · 1-line narration gist · payoff) and get a nod before rendering. Rendering a
5-scene clip takes ~3–6 min; do not render before the nod.

## 2. Scene spec

```yaml
clip: 1-setup                 # output name → out/1-setup.mov
voice: onyx
instructions: "Calm, clear, confident tech-demo narration. Medium pace, natural pauses at the dots. Slight emphasis on numbers."
scenes:
  - id: s1                    # short, stable ids → cache keys
    caption: "Thesis · one graph, four evidences"     # lower-third; keep ≤ 60 chars
    narration: "…25–45 words…"                        # write numbers as words if TTS mangles them ("eighteen thousand")
    # exactly one capture source per scene:
    url: "http://127.0.0.1:4300/#mode=purchase"       # (a) browser via Playwright — plus optional actions:
    actions:                                          #     run after load, in order; `ready` marks the payoff
      - fill: ["#prompt", "Acne Studios"]
      - press: ["#prompt", "Enter"]
      - wait: ".layer-chip"                           #     selector (45 s timeout) → sets ready
      - click: "button:has-text('fit')"
      - select: ["#graph-layout", "brand"]
      - scroll_to: "#join"                            #     scrollIntoView (for long documents) → sets ready
      - hover: ".card"
    # video: "cache/cr_s3"                            # (b) pre-recorded dir (page.mov + marks.json) or a file — see record_screen.sh
    # still: "docs/figure.png"                        # (c) a static image (chart, slide) — Ken-Burns-free, held for the narration
    hold: 2                                           # extra seconds after the last action
    speed: 1                                          # pre-speed the source (8 = a slow crawl shown at 8×)
    scale: 2560                                       # per-scene downscale width (screen recordings); font: 28 = caption px for this scene
```

Rules that made the clips good:
- **Payoff first.** The renderer starts each scene ~2.5 s *before* `ready`, pads the last frame if the narration is longer, trims if shorter.
  A scene whose payoff is at second 40 of a 45 s recording becomes a 12 s scene that opens on the payoff.
- **Narration and screen agree.** Every capitalised name and every number in the narration must be visible or about to be visible. Cut sentences that aren't.
- **One idea per scene.** If a sentence starts with "also", it is a new scene or it is cut.
- **Captions are the outline.** Reading only the captions should give the whole story.
- **Never fabricate a number for narration.** Take it from a result file or a live response you just made; say "about" if rounded.

## 3. Capture sources

- **Browser (`url` + `actions`)** — Playwright Chromium, 1440×900, headless, records webm. Needs a Node project with `@playwright/test` and
  Chromium installed; set `PW_REPO=/path/to/that/project` (default: the skill's own `pw/` — run `scripts/setup.sh` once to create it).
- **Screen / terminal (`video`)** — `scripts/record_screen.sh <scene> <seconds> -- <command that performs the action>`: starts
  `screencapture -V`, runs your command, writes `marks.json` with `started` (ms) when the command signals the payoff by printing `MARK`.
  **Gotcha:** `screencapture -V` only advances when pixels change; a static terminal pane freezes the recording. Keep something ticking
  (a 1 Hz clock line) or use `show_file.sh` which pages a file with a clock. Downscale wide captures with `DEMO_SCALE=2560`.
- **Still (`still`)** — a PNG/JPG held for the narration; use for charts, tables, a slide.
- **Pre-recorded (`video: file.mov`)** — with `ready: <seconds>` in the scene.

## 4. Render, review, post

```bash
export OPENAI_API_KEY=…                     # TTS (gpt-4o-mini-tts); or TTS_URL=https://<proxy>/v1/audio/speech TTS_API_KEY=… for a compatible proxy
scripts/render_clip.py clips/1-setup.yaml            # full clip → out/1-setup.mov (+ out/_1-setup_<scene>.png stills)
scripts/render_clip.py clips/1-setup.yaml --only s2  # re-render one scene, re-concat
DEMO_FONT=26 scripts/render_clip.py …                # caption size (22 for 1440 px, 26–30 for 2560 px sources)
```

Review: `read` two or three of the `out/_*.png` stills. If a browser scene logs `wait failed: … Timeout`, the app was slow or the selector changed: the scene still renders from t=0 (no payoff cut) — fix the selector or just re-run that scene with `--only <id>` when the app is idle (opening frame of each scene) — check the caption is legible, the payoff is on screen,
nothing sensitive is visible (tokens, buyer-level rows, other people's messages). Watch the first and last 5 s of the `.mov` if you can.

Post to Slack with a blurb of ≤ 3 lines: what it shows · length · one number. `scripts/slack_post.py C0123… out/1-setup.mov "…"` uses the
`slack-mcp` browser session credentials in `~/.config/slack-mcp/credentials.json`; if absent, hand the user the file and the blurb.

## 5. Conventions (keep the project tidy)

`clips/` specs · `cache/` TTS + per-scene video (gitignored) · `out/` finals + stills · `blurbs/` Slack text. Name clips in play order
(`0-…`, `1-…`, `2a-…`). Keep a `storyboard.md` with the table from the interview; it is the artefact people ask for after the video.

Dependencies: `ffmpeg`/`ffprobe`, `node` ≥ 18, Playwright Chromium (for browser scenes), macOS `screencapture` (for screen scenes), a TTS key.
`scripts/setup.sh` checks and installs what it can.
