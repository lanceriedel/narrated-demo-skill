# narrated-demo

**A pi / Claude Code skill that turns the work an agent is already doing into a short, narrated demo video.**

You say *"make a demo video of this"*. The agent asks five questions, drafts a storyboard from the context it is already in, and renders a
captioned, voice-over `.mov` — browser walkthroughs, terminal recordings, documents, stills — that a VP can watch on a phone. Everything
is a text file you can edit and re-render in seconds.

Built while shipping a real project (five clips, 69–188 s each, rendered and re-rendered dozens of times); the skill is that pipeline
with the project-specific parts removed and the lessons written down.

---

## Table of contents

- [What you get](#what-you-get)
- [How it works](#how-it-works)
- [Install](#install)
- [Quick start](#quick-start)
- [The interview](#the-interview)
- [The scene spec](#the-scene-spec)
- [Capture types](#capture-types)
- [Rendering and iterating](#rendering-and-iterating)
- [Rules that make clips good](#rules-that-make-clips-good)
- [Posting to Slack](#posting-to-slack)
- [Project layout](#project-layout)
- [Troubleshooting](#troubleshooting)
- [How it is built](#how-it-is-built)
- [Sharing and contributing](#sharing-and-contributing)

---

## What you get

| you provide | the agent produces |
|---|---|
| answers to 5 questions (or "you decide") | `storyboard.md` — a table: scene · on screen · narration gist · payoff |
| a nod on the storyboard | `clips/<name>.yaml` — the scene spec (narration, captions, what to capture and how) |
| — | `out/<name>.mov` — H.264, AAC, faststart; one scene per idea; lower-third captions |
| — | `out/_<name>_<scene>.png` — the opening frame of every scene, for review |
| a channel id (optional) | the clip posted to Slack with a 3-line blurb |

Typical numbers: a 5-scene, 90-second clip takes ~15 minutes from "make a video" to a reviewable `.mov`, and ~20 seconds to re-render one
scene after you change a sentence.

## How it works

```
   interview ──► storyboard ──► scene spec ──► per scene: TTS ─┐
   (5 Qs)         (table)       (yaml)                          ├─► fit video to audio ──► caption ──► segment ─┐
                                              capture ──────────┘   (payoff first,                              ├─► concat ──► out/<clip>.mov
                                              browser | screen | still  freeze/trim)                            │
                                                                                                                 └─► review stills
```

- **TTS** — `gpt-4o-mini-tts` (OpenAI-compatible endpoint; defaults to Shopify's `proxy.shopify.ai`, works with `api.openai.com`). Cached by
  a hash of *voice + instructions + text*, so unchanged sentences never re-synthesise.
- **Capture** — browser scenes are driven by Playwright (headless Chromium, 1440×900, records webm); screen/terminal scenes use macOS
  `screencapture -V`; stills are held for the length of the narration.
- **Fit** — the renderer knows *when the payoff appeared* (`ready`) and starts the scene ~2.5 s before it. If the narration is longer than
  the footage it freezes the last frame; if shorter it trims. So a 45-second recording whose interesting moment is at second 40 becomes a
  12-second scene that opens on the interesting moment.
- **Caption** — one lower-third per scene (ffmpeg `drawtext`), so reading only the captions gives the whole story.
- **Concat** — segments joined into one `.mov`.

## Install

Requirements: macOS (for screen scenes; browser and still scenes work anywhere), `ffmpeg`, `node` ≥ 18, a TTS key.

```bash
git clone https://github.com/lanceriedel/narrated-demo-skill ~/.agents/skills/narrated-demo
~/.agents/skills/narrated-demo/scripts/setup.sh        # checks ffmpeg/node/key; installs Playwright + Chromium into the skill's own pw/
export PI_PROXY_API_KEY=…                                # Shopify proxy; or OPENAI_API_KEY + TTS_URL=https://api.openai.com/v1/audio/speech
```

- **pi** discovers `~/.agents/skills/*/SKILL.md` automatically. Use `/skill:narrated-demo` or just ask.
- **Claude Code** — add the directory to your skills settings (see your harness docs), or copy `SKILL.md` into `.claude/skills/narrated-demo/`.
- Optional: `~/.config/slack-mcp/credentials.json` (from the `slack-mcp` browser session) enables `scripts/slack_post.py`.

## Quick start

In an agent session that already has context on what you built:

> make a 90-second demo video of this for Daniel — he has a minute

The agent will ask the five questions, propose a storyboard table, and after your nod run something equivalent to:

```bash
scripts/render_clip.py clips/1-setup.yaml            # → out/1-setup.mov + out/_1-setup_*.png
```

Or drive it yourself: copy `examples/1-setup.yaml`, edit, render.

## The interview

Five questions, asked in one message. Partial answers are fine; the agent fills the rest from context and labels what it assumed.

| # | question | what it decides |
|---|---|---|
| 1 | **Who is it for, and how long do they have?** (peer engineer 3 min · exec 90 s · Slack scroll 60 s) | scene count, pace, how much to explain |
| 2 | **What is the one thing they should believe after watching?** | scene 1's first sentence and the last scene's last sentence |
| 3 | **What must be on screen?** (a UI, a terminal, a document, a chart) — URLs, commands, paths | capture types |
| 4 | **What is the "live" moment?** something that visibly *happens* — a query returning, a build finishing, a number appearing | the payoff scene; every clip needs at least one |
| 5 | **Voice and tone?** default `onyx`, "calm, clear, confident tech-demo narration" | TTS voice + instructions |

Then the storyboard table, then the nod, then rendering. Rendering before the nod wastes 3–6 minutes per attempt; the table costs 30 seconds to read.

## The scene spec

`clips/<name>.yaml` — a deliberately small YAML subset (no external parser needed):

```yaml
clip: 1-setup                 # → out/1-setup.mov
voice: onyx
instructions: "Calm, clear, confident tech-demo narration. Medium pace, natural pauses at the dots. Slight emphasis on numbers."
scenes:
  - id: s1-thesis             # short, stable ids: they are the cache keys
    caption: "One graph · four kinds of evidence"       # ≤ 60 chars
    narration: "…25–45 words ≈ 10–18 s spoken…"
    still: "docs/figures/thesis.png"                     # capture type (a): a static image

  - id: s2-live
    caption: "Live · a seed, a walk, under a second"
    narration: "Type a brand. …"
    url: "http://127.0.0.1:4300/#mode=purchase"          # capture type (b): browser + actions
    actions:
      - fill: ["#prompt", "Acne Studios"]
      - press: ["#prompt", "Enter"]
      - wait: ".layer-chip"                              # ← sets the payoff time
      - click: "button:has-text('fit')"
    hold: 3                                              # seconds to linger after the last action

  - id: s3-terminal
    caption: "One command · a worker · a result"
    narration: "…"
    video: "cache/cr_s3"                                 # capture type (c): pre-recorded dir (page.mov + marks.json) or a file
    speed: 1                                             # 8 = show a slow process at 8×
```

Every scene has **exactly one** capture source: `still`, `url`, or `video`.

### Actions (browser scenes)

| verb | argument | effect |
|---|---|---|
| `fill` | `[selector, text]` | clear and type |
| `press` | `[selector, key]` | e.g. `Enter` |
| `click` | `selector` | Playwright selector; `button:has-text('fit')` works |
| `select` | `[selector, value]` | `<select>` option |
| `hover` | `selector` | hover 1.2 s (tooltips) |
| `wait` | `selector` | wait up to 45 s for it to appear, **mark the payoff**, linger 2.5 s |
| `wait_ms` | `ms` | plain pause |
| `scroll_to` | `selector` | smooth `scrollIntoView`, **mark the payoff** (long documents) |
| `mark` | — | mark the payoff now |
| `eval` | `js` | escape hatch |

If no action marks the payoff, the scene starts at t = 0.

## Capture types

**Browser (`url` + `actions`)** — any URL Chromium can open, including `file:///…/doc.html` for documents (use `scroll_to` anchors as
scenes). Headless, so it does not need your screen and does not interrupt you. Viewport 1440×900. Set `PW_REPO` to reuse an existing
Playwright install instead of the skill's `pw/`.

**Screen / terminal (`video`)** — for things a browser cannot show: a terminal multiplexer, a native app, your real desktop.

```bash
scripts/record_screen.sh cache/cr_s3 60 -- ./do_the_thing.sh      # records 60 s; when the command prints a line containing MARK, that is the payoff
```

Writes `cache/cr_s3/page.mov` + `marks.json`; reference the directory as `video:`. Downscale wide screens for legible captions with
`DEMO_SCALE=2560 DEMO_FONT=28`.

> **Gotcha, learned the hard way:** `screencapture -V` only advances when pixels change. A static terminal pane will *freeze the
> recording* and the capture never finishes. Keep something ticking on screen — `scripts/show_file.sh <file>` pages a file with a 1 Hz clock
> line for exactly this reason — or make sure the command keeps producing visible output.

**Still (`still`)** — a PNG/JPG held for the narration. Charts, a slide, a table screenshot, the storyboard itself. Even dimensions are enforced.

**Pre-recorded (`video: file.mov`, `ready: 12`)** — anything you already have; give the payoff second by hand.

## Rendering and iterating

```bash
scripts/render_clip.py clips/1-setup.yaml                 # whole clip
scripts/render_clip.py clips/1-setup.yaml --only s2       # re-render one scene, re-concat (others come from cache)
scripts/render_clip.py clips/1-setup.yaml --voice nova    # try another voice (TTS re-synthesised, video cached)
DEMO_FONT=26 scripts/render_clip.py …                     # caption size: 22 for 1440-px sources, 26–30 for 2560-px screen recordings
```

Outputs go to `./out/` and `./cache/` relative to where you run it (or `--out DIR`).

**Review before you declare done.** Open two or three `out/_<clip>_<scene>.png` stills (the agent uses its image-reading tool): is the
caption legible, is the payoff on screen, is anything sensitive visible (tokens, private rows, other people's messages)? Watch the first
and last five seconds of the `.mov`.

Iteration is cheap by design: change one sentence → one TTS call → one 20-second mux. Change one selector → one 30-second capture.

## Rules that make clips good

These came out of making the same five clips many times. The skill enforces the mechanical ones and reminds the agent of the rest.

1. **Payoff first.** Cut so the interesting moment is on screen within ~2.5 s of the scene starting. Nobody waits 40 s for a spinner.
2. **Narration and screen agree.** Every capitalised name and every number spoken must be visible or about to be. Cut sentences that aren't.
3. **One idea per scene.** If a sentence starts with "also", it is a new scene or it is cut.
4. **Captions are the outline.** Reading only the captions should give the whole story.
5. **25–45 words per scene.** ≈ 10–18 s spoken. Longer scenes lose phone viewers; shorter ones feel like a slideshow.
6. **Write numbers as words when TTS mangles them** ("eighteen thousand one hundred and thirty-two tables").
7. **Never fabricate a number for narration.** Take it from a result file or a live response you just made; say "about" if rounded. A demo
   that states a wrong number is worse than no demo.
8. **The storyboard is the artefact people ask for afterwards.** Keep `storyboard.md` next to the clips.

## Posting to Slack

```bash
scripts/slack_post.py C0123ABCD out/1-setup.mov "*Setup (69 s)* — thesis → live crawl at 8× → purchase-graph mode. 155 M edges, one lookup."
```

Uses the `slack-mcp` browser-session credentials (`~/.config/slack-mcp/credentials.json`): `files.getUploadURLExternal` → upload →
`files.completeUploadExternal` with the blurb as the message. If the credentials are absent, the agent hands you the file and the blurb.

Blurb rule: ≤ 3 lines — what it shows · length · one number.

## Project layout

```
your-project/
  storyboard.md          # the table from the interview (commit it)
  clips/                 # scene specs, named in play order: 0-…, 1-…, 2a-…   (commit)
  cache/                 # tts_<hash>.mp3, vid_<scene>/, seg_<clip>_NN.mp4     (gitignore)
  out/                   # <clip>.mov + _<clip>_<scene>.png review stills      (commit finals if you like)
  blurbs/                # Slack text per clip                                  (commit)
```

Skill layout:

```
SKILL.md                 # what the agent reads: workflow, interview, spec, rules
scripts/render_clip.py   # the renderer (python3 + ffmpeg + node/Playwright)
scripts/record_screen.sh # screencapture -V wrapper with MARK → payoff time
scripts/show_file.sh     # page a file with a 1 Hz clock (keeps screen captures alive)
scripts/slack_post.py    # upload + message
scripts/setup.sh         # dependency check / Playwright install into pw/
examples/1-setup.yaml    # a real spec, generalised
examples/storyboard.md   # template
```

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| `[s2] wait failed: … Timeout 45000ms` and the scene starts on an empty page | the app was slow/busy, or the selector changed | check the selector in the app's HTML; re-run `--only s2` when the app is idle |
| `no video for scene … is PW_REPO set up?` | Playwright/Chromium missing | `scripts/setup.sh`, or `PW_REPO=/path/to/project-with-playwright` |
| `TTS HTTP 400/401` | key missing/expired, or model not on that endpoint | check `PI_PROXY_API_KEY` / `OPENAI_API_KEY`; set `TTS_MODEL` / `TTS_URL` |
| screen recording is 2 s long / never finishes | static screen — `screencapture -V` only advances on pixel change | keep a clock ticking (`show_file.sh`) or produce output continuously |
| caption tiny / huge | source resolution ≠ 1440 px | `DEMO_FONT=26–30` for 2560-px sources; `DEMO_SCALE=2560` to downscale 5K captures |
| narration cuts off | segment is `audio + 0.6 s`; a trailing "hold" is video-only | end narration with a full stop; add `hold: 2` |
| numbers mispronounced | TTS reads "155M" as letters | write "one hundred and fifty-five million" |
| `drawtext` font error on Linux | default font path is macOS | `DEMO_FONTFILE=/usr/share/fonts/…/DejaVuSansMono.ttf` |

## How it is built

Deliberately boring: **python3 stdlib + ffmpeg + one Node script for Playwright**. No video libraries, no framework, no service.

- `render_clip.py` parses a small YAML subset itself (top-level keys, a `scenes` list, an `actions` list per scene) so the skill has zero
  Python dependencies. Full YAML is not supported on purpose; the spec stays readable.
- The Playwright driver is a string inside the Python file, written to `<PW_REPO>/.demo/scene.mjs` at run time; it records a webm and writes
  `marks.json` with `ready` (ms since start) when an action marks the payoff.
- ffmpeg does the rest with one filter graph per scene: `trim → setpts → fps=30 → [scale] → tpad (freeze last frame) → drawtext`, cut to the
  audio length with `-t`. `tpad=stop=-1` plus `-t` is what makes the "freeze if narration is longer" behaviour robust against Playwright's
  sparse webm timestamps.
- Stills are looped with `-loop 1` and cut the same way.
- Concat uses the ffmpeg concat demuxer; all segments share codec, fps and pixel format so it never re-encodes badly.

## Sharing and contributing

MIT (see LICENSE): take it, change it. Useful additions would be a Linux screen recorder (`wf-recorder`/`ffmpeg x11grab`) behind
`record_screen.sh`, a `zoom` action for browser scenes, and per-scene background music ducked under narration. Keep the spec small.

Origin: built for a taste-graph demo at Shopify (five clips: setup, edges ×2, how-it-was-built, control-room). The control-room clip is where
the "static pane freezes screencapture" lesson and the 1 Hz clock trick came from.
