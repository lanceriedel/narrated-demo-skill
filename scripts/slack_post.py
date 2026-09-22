#!/usr/bin/env python3
"""Post a file + message to a Slack channel using the slack-mcp browser session (~/.config/slack-mcp/credentials.json).

  scripts/demo/slack_post.py <channel_id> <file> "<message>"   (message may be multi-line; Slack mrkdwn)
Uses files.getUploadURLExternal -> POST bytes -> files.completeUploadExternal (shares into channel with initial_comment).
"""
import json, os, subprocess, sys
from pathlib import Path

CRED = json.load(open(Path.home() / ".config/slack-mcp/credentials.json"))
HDR = ["-H", f"Authorization: Bearer {CRED['token']}", "-H", f"Cookie: d={CRED['cookie']}"]

def api(method, **form):
    args = ["curl", "-s", f"https://slack.com/api/{method}", *HDR]
    for k, v in form.items(): args += ["--data-urlencode", f"{k}={v}"]
    out = json.loads(subprocess.run(args, capture_output=True, text=True).stdout)
    if not out.get("ok"): raise SystemExit(f"{method} failed: {out}")
    return out

def main():
    channel, path, msg = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    up = api("files.getUploadURLExternal", filename=path.name, length=path.stat().st_size)
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-X", "POST", up["upload_url"], "-F", f"file=@{path}"], capture_output=True, text=True)
    if r.stdout.strip() != "200": raise SystemExit(f"upload HTTP {r.stdout}")
    done = api("files.completeUploadExternal", files=json.dumps([{"id": up["file_id"], "title": path.stem}]), channel_id=channel, initial_comment=msg)
    f = done["files"][0]; print(f"posted {path.name} → {channel}  file {f['id']}  {f.get('permalink','')}")

if __name__ == "__main__": main()
