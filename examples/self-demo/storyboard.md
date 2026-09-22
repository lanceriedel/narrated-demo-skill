# Storyboard — narrated-demo in 75 s (for people you'd share the repo with · Slack-scroll length)

**They should believe:** an agent that already knows your work can produce a watchable, narrated demo in minutes — from a text file you can edit.

| # | scene | on screen | narration gist | payoff |
|---|---|---|---|---|
| 1 | the ask | terminal: `› make a 90-second demo video of this for Daniel` | you ask in plain words; the agent has the context | the line |
| 2 | interview | SKILL.md §1 paged in a pane | five questions decide scenes, pace, payoff; storyboard approved before rendering | the table |
| 3 | spec | this clip's own `clips/self.yaml` | narration + caption + one capture; `wait` marks the payoff | the yaml |
| 4 | render (live) | terminal running `render_clip.py clips/mini.yaml` | TTS cached by hash → capture → fit → caption → concat | `→ out/mini.mov (7s)` |
| 5 | review | a review still (`out/_mini_s1.png`) | read the stills before saying done; one sentence → one scene → 20 s | the still |
| 6 | share | github.com/lanceriedel/narrated-demo-skill | clone → setup.sh → ask; MIT | the README |

Voice: onyx · tone: calm tech-demo · rendered 91 s (narration ran long on 2 and 4; fine for the audience).
Lesson logged during review: an inline `export TTS_API_KEY=…` in the recorded pane put the key on screen — caught by the still, re-recorded with the key from the shell env.
