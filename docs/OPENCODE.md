# Using clipper with OpenCode

OpenCode reads this repository's `AGENTS.md` and the skill in `.agents/skills/clipping/` automatically when you open it in the folder. No copying is needed.

## 1. Get the code

```powershell
git clone https://github.com/marcxxv/clipper.git
cd clipper
opencode
```

## 2. Paste this prompt into OpenCode

It sets everything up and asks before doing anything unexpected. Copy everything inside the box:

```text
Set up this repository (the "clipper" video clipping pipeline) on my computer.

1. Read README.md, AGENTS.md, docs/SETUP.md and .agents/skills/clipping/SKILL.md first.
2. Run the setup script for my operating system:
   - Windows:  powershell -ExecutionPolicy Bypass -File setup\setup.ps1
   - macOS/Linux:  bash setup/setup.sh
   If a step fails, read the error, fix it using docs/SETUP.md (Troubleshooting), and run the script again.
   Ask me before installing anything that the setup script does not install itself.
3. NYO API key: if .env has no NYO_API_KEY yet, ask me for my key and write it into .env
   as NYO_API_KEY=<key>. Never print the key back, never commit .env.
4. NYO in OpenCode: check my OpenCode config. If I already have an NYO provider with
   glm-5.3-flash, keep it. Otherwise copy integrations/opencode/opencode.json to the repo
   root as opencode.json (it is git-ignored) and tell me to set the NYO_API_KEY environment
   variable (Windows: setx NYO_API_KEY "<key>", then restart OpenCode).
5. Run the self-test and show me the result:
   - Windows:  pipeline\.venv\Scripts\python.exe pipeline\clips.py --check
   - macOS/Linux:  pipeline/.venv/bin/python pipeline/clips.py --check
   Every line must say "ok". Fix anything that says "NO".
6. Tell me in 3 short lines: what was installed, whether the check passed, and the exact
   command to clip a YouTube link.
```

## 3. Daily use

Just ask, for example:

- *"Clip this: https://youtu.be/…"*
- *"Re-edit the trailer in sources into shorts."*
- *"The campaign wants 30–60 second clips. Set that up and re-run the last video."*
- *"Show me the report for the last video."*

The agent follows the skill: it runs the pipeline, reads `report.md`, checks real frames, and asks before posting anything or using footage you don't have rights to.

## Model

`integrations/opencode/opencode.json` adds NYO as a provider and makes `glm-5.3-flash` the default. It's cheap: about $0.15 per million tokens. Switch with `/models`. The pipeline's own AI calls use NYO through `.env` whatever model OpenCode chats with.

## Keeping up to date

Ask OpenCode *"pull the latest version and re-run setup if requirements changed"*, or run `git pull` yourself.
