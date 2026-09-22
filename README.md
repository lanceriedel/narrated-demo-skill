# narrated-demo — a pi/Claude skill that turns your current work into a narrated demo video

Interview (5 questions) → storyboard → scene spec → TTS + browser/screen captures + captions → one `.mov`. Proven on five clips.

Install (pi): `git clone https://github.com/lanceriedel/narrated-demo-skill ~/.agents/skills/narrated-demo && ~/.agents/skills/narrated-demo/scripts/setup.sh`
Then in pi: `/skill:narrated-demo` or just ask for "a demo video of this". Claude Code: add the directory to your skills settings.

See `SKILL.md` for the workflow and `examples/` for a spec and a storyboard template.
