# Using clipper with Hermes

A Hermes profile named `clipper` runs the pipeline as an agent. It uses NYO `glm-5.3-flash` by default and falls back to `qwen3-30b`.

## Install (macOS / Linux)

```bash
bash integrations/hermes/install.sh
clipper chat
```

The script is safe to re-run. It:

1. creates the `clipper` profile if it doesn't exist, with `integrations/hermes/config.yaml.example` as its config. Its terminal starts in this repo;
2. **links** (doesn't copy) the profile's skill and identity to this repo:
   - `~/.hermes/profiles/clipper/skills/media/clipping` → `.agents/skills/clipping`
   - `~/.hermes/profiles/clipper/SOUL.md` → `integrations/hermes/SOUL.md`

   It backs up any real file it replaces as `*.bak-YYYYMMDD`;
3. copies `NYO_API_KEY` from the repo's `.env` into the profile's `.env` as `HERMES_CUSTOM_NYOLAB_API_KEY` if the profile has no key yet.

Because of the links, a `git pull` updates the agent too. There's one copy of the rules.

## What stays in the profile (not in git)

- `config.yaml`: the model and paths. An existing one is never overwritten. To change the model, edit it, or start from the example again.
- `.env`: the key.
- Sessions and memory.

## Changing things

Change the skill, docs or code **in the repo**, then commit and push (see `AGENTS.md`).

## Windows

Hermes runs on macOS and Linux. On Windows, use OpenCode instead ([OPENCODE.md](OPENCODE.md)): it reads the same skill and rules.
