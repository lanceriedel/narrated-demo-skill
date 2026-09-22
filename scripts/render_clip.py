#!/usr/bin/env python3
"""Render a narrated demo clip from a scene spec (see SKILL.md §2).

  render_clip.py clips/<name>.yaml [--only s2,s3] [--voice onyx] [--out DIR]

Per scene: TTS (gpt-4o-mini-tts via $TTS_URL, default api.openai.com; key $TTS_API_KEY or $OPENAI_API_KEY) → mp3, cached by text hash;
capture (browser via Playwright | pre-recorded video | still image) → video; ffmpeg starts the video ~2.5 s before the payoff (`ready`),
pads the last frame if narration is longer, trims if shorter, burns a lower-third caption, muxes; scenes concatenated → out/<clip>.mov.
Also writes out/_<clip>_<scene>.png (opening frame of each scene) for review.
Env: PW_REPO (Node project with @playwright/test + chromium; default <skill>/pw), DEMO_FONT (caption px, 22), DEMO_SCALE (downscale width),
     DEMO_FONTFILE (default /System/Library/Fonts/SFNSMono.ttf), TTS_URL, TTS_MODEL (gpt-4o-mini-tts).
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
CWD = Path.cwd()
PW_REPO = Path(os.environ.get("PW_REPO", str(SKILL / "pw")))
TTS_URL = os.environ.get("TTS_URL", "https://api.openai.com/v1/audio/speech")
TTS_MODEL = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")


def parse_spec(path):
    """YAML subset: top-level `key: value`; `scenes:` with `- key: value` items; nested `actions:` as a list of `- verb: value|[a, b]`."""
    spec = {"scenes": []}; cur = None; in_actions = False
    for raw in Path(path).read_text().splitlines():
        if not raw.strip() or raw.strip().startswith("#"): continue
        indent = len(raw) - len(raw.lstrip(" ")); s = raw.strip()
        if indent == 0:
            k, _, v = s.partition(":"); in_actions = False
            if k.strip() != "scenes": spec[k.strip()] = _val(v)
            continue
        if indent == 2 and s.startswith("- "):
            cur = {}; spec["scenes"].append(cur); s = s[2:]; in_actions = False
        if in_actions and indent >= 6 and s.startswith("- "):
            verb, _, v = s[2:].partition(":"); cur["actions"].append({verb.strip(): _val(v)}); continue
        k, _, v = s.partition(":"); k = k.strip()
        if k == "actions" and not v.strip():
            cur["actions"] = []; in_actions = True; continue
        in_actions = False; cur[k] = _val(v)
    return spec


def _val(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [_val(x) for x in _split_list(v[1:-1])]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'": return v[1:-1]
    return v


def _split_list(s):
    out, buf, q = [], "", None
    for ch in s:
        if q:
            buf += ch
            if ch == q: q = None
        elif ch in "\"'": q = ch; buf += ch
        elif ch == ",": out.append(buf.strip()); buf = ""
        else: buf += ch
    if buf.strip(): out.append(buf.strip())
    return out


def tts(text, voice, instructions, cache):
    h = hashlib.sha1(f"{TTS_MODEL}|{voice}|{instructions}|{text}".encode()).hexdigest()[:16]
    mp3 = cache / f"tts_{h}.mp3"
    if mp3.exists(): return mp3
    key = os.environ.get("TTS_API_KEY") or os.environ.get("OPENAI_API_KEY") or sys.exit("set OPENAI_API_KEY (or TTS_API_KEY + TTS_URL for a compatible proxy)")
    body = json.dumps({"model": TTS_MODEL, "voice": voice, "input": text, "instructions": instructions, "format": "mp3"})
    r = subprocess.run(["curl", "-s", "-m", "120", "-o", str(mp3), "-w", "%{http_code}", TTS_URL, "-H", f"Authorization: Bearer {key}",
                        "-H", "Content-Type: application/json", "-d", body], capture_output=True, text=True)
    if r.stdout.strip() != "200": mp3.unlink(missing_ok=True); sys.exit(f"TTS HTTP {r.stdout}: {text[:60]}")
    return mp3


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


PW_SCRIPT = r"""
import { chromium } from '@playwright/test';
import { writeFileSync } from 'node:fs';
const t0 = Date.now(); let ready = 0;
const scene = JSON.parse(process.argv[2]); const out = process.argv[3];
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, recordVideo: { dir: out, size: { width: 1440, height: 900 } } });
const page = await ctx.newPage(); const pause = (ms) => page.waitForTimeout(ms);
await page.goto(scene.url, { waitUntil: 'networkidle' }).catch(() => page.goto(scene.url)); await pause(900);
const mark = () => { if (!ready) ready = Date.now() - t0; };
for (const step of (scene.actions || [])) {
  const [verb, arg] = Object.entries(step)[0];
  try {
    if (verb === 'fill') { await page.fill(arg[0], ''); await page.fill(arg[0], arg[1]); await pause(400); }
    else if (verb === 'press') { await page.locator(arg[0]).press(arg[1]); }
    else if (verb === 'click') { await page.locator(arg).first().click(); await pause(600); }
    else if (verb === 'select') { await page.selectOption(arg[0], arg[1]); await pause(800); }
    else if (verb === 'hover') { await page.locator(arg).first().hover(); await pause(1200); }
    else if (verb === 'wait') { await page.waitForSelector(arg, { timeout: 45000 }); mark(); await pause(2500); }
    else if (verb === 'wait_ms') { await pause(Number(arg)); }
    else if (verb === 'mark') { mark(); }
    else if (verb === 'scroll_to') { const el = page.locator(arg).first(); if (await el.count()) { await el.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'start' })); mark(); await pause(1500); } }
    else if (verb === 'eval') { await page.evaluate(arg); }
  } catch (e) { console.error(`[${scene.id}] ${verb} failed: ${e.message.split('\n')[0]}`); }
}
await pause(Number(scene.hold || 2) * 1000);
writeFileSync(`${out}/marks.json`, JSON.stringify({ ready, total: Date.now() - t0 }));
await ctx.close(); await browser.close();
"""


def record_browser(scene, cache):
    vdir = cache / f"vid_{scene['id']}"; vdir.mkdir(exist_ok=True)
    for f in vdir.glob("*.webm"): f.unlink()
    (PW_REPO / ".demo").mkdir(parents=True, exist_ok=True); (PW_REPO / ".demo" / "scene.mjs").write_text(PW_SCRIPT)
    r = subprocess.run(["node", ".demo/scene.mjs", json.dumps(scene), str(vdir)], cwd=PW_REPO, capture_output=True, text=True)
    if r.stderr.strip(): print("\n   " + r.stderr.strip().replace("\n", "\n   "))
    vids = sorted(vdir.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if not vids: sys.exit(f"no video for scene {scene['id']} (is PW_REPO={PW_REPO} set up? run scripts/setup.sh)")
    marks = json.loads((vdir / "marks.json").read_text()) if (vdir / "marks.json").exists() else {}
    return vids[-1], marks.get("ready", 0) / 1000


def source_for(scene, cache):
    if scene.get("still"):
        return Path(scene["still"]), 0.0, True
    if scene.get("video"):
        v = Path(scene["video"])
        if v.is_dir():
            vids = sorted(list(v.glob("*.webm")) + list(v.glob("*.mov")) + list(v.glob("*.mp4")))
            marks = json.loads((v / "marks.json").read_text()) if (v / "marks.json").exists() else {}
            return vids[-1], float(scene.get("ready", marks.get("started", marks.get("ready", 0)) / 1000)), False
        return v, float(scene.get("ready", 0)), False
    if scene.get("url"):
        v, ready = record_browser(scene, cache); return v, ready, False
    sys.exit(f"scene {scene['id']}: needs one of url | video | still")


def fit_and_mux(video, audio, caption, out_mp4, ready=0.0, speed=1.0, still=False):
    va = duration(audio) + 0.6
    font = os.environ.get("DEMO_FONTFILE", "/System/Library/Fonts/SFNSMono.ttf")
    capf = out_mp4.with_suffix(".caption.txt"); capf.write_text(caption or "")
    draw = (f"drawtext=textfile='{capf}':fontcolor=white:fontsize={os.environ.get('DEMO_FONT', '22')}:box=1:boxcolor=black@0.6:boxborderw=12:"
            f"x=36:y=h-110:fontfile={font}") if caption else "null"
    sc = os.environ.get("DEMO_SCALE"); pre = f"scale={sc}:-2," if sc else ""
    if still:
        vf = f"[0:v]{pre}scale=trunc(iw/2)*2:trunc(ih/2)*2,{draw}[v]"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(video), "-i", str(audio), "-filter_complex", vf]
    else:
        if speed != 1.0:
            fast = out_mp4.with_suffix(".fast.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-an", "-vf", f"setpts=PTS/{speed}", "-r", "30", "-c:v", "libx264", "-crf", "18", str(fast)], check=True)
            video, ready = fast, ready / speed
        start = max(0.0, ready - 2.5)
        vf = f"[0:v]trim=start={start:.2f},setpts=PTS-STARTPTS,fps=30,{pre}tpad=stop=-1:stop_mode=clone,{draw}[v]"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio), "-filter_complex", vf]
    subprocess.run(cmd + ["-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k",
                          "-t", f"{va:.2f}", str(out_mp4)], check=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args: sys.exit(__doc__)
    spec = parse_spec(args[0])
    opt = lambda name, default=None: next((sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == name), default)
    only = set((opt("--only") or "").split(",")) - {""}
    out = Path(opt("--out", str(CWD / "out"))); cache = CWD / "cache"; out.mkdir(parents=True, exist_ok=True); cache.mkdir(exist_ok=True)
    voice = opt("--voice", spec.get("voice", "onyx"))
    instr = spec.get("instructions", "Calm, clear, confident tech-demo narration. Medium pace. Slight emphasis on numbers.")
    parts = []
    for i, sc in enumerate(spec["scenes"]):
        seg = cache / f"seg_{spec['clip']}_{i:02d}.mp4"
        if only and sc["id"] not in only and seg.exists():
            parts.append(seg); print(f"[{sc['id']}] cached"); continue
        print(f"[{sc['id']}] tts…", end=" ", flush=True); a = tts(sc["narration"], voice, instr, cache); print(f"{duration(a):.1f}s · capture…", end=" ", flush=True)
        v, ready, still = source_for(sc, cache)
        print(("still" if still else f"{duration(v):.1f}s (ready {ready:.0f}s)") + " · mux…", end=" ", flush=True)
        fit_and_mux(v, a, sc.get("caption", ""), seg, ready, float(sc.get("speed", 1)), still); parts.append(seg)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", str(seg), "-frames:v", "1", str(out / f"_{spec['clip']}_{sc['id']}.png")])
        print("ok")
    lst = cache / f"concat_{spec['clip']}.txt"; lst.write_text("".join(f"file '{p}'\n" for p in parts))
    final = out / f"{spec['clip']}.mov"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(final)], check=True)
    print(f"\n→ {final}  ({duration(final):.0f}s, {final.stat().st_size/1e6:.1f} MB)   stills: {out}/_{spec['clip']}_*.png")


if __name__ == "__main__": main()
