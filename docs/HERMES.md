# Using clipper with Hermes

A Hermes profile named `clipper` runs the pipeline as an agent. It uses NYO `glm-5.3-flash` by default and falls back to `qwen3-30b`.

## Install (macOS / Linux)

```bash
bash integrations/hermes/install.sh
hermes -p clipper
```

The script is safe to re-run. It:

1. creates the `clipper` profile if it doesn't exist, with `integrations/hermes/config.yaml.example` as its config. Its terminal starts in this repo;
2. **links** (doesn't copy) the profile's skill and identity to this repo:
   - `~/.hermes/profiles/clipper/skills/media/clipping` → `.agents/skills/clipping`
   - `~/.hermes/profiles/clipper/SOUL.md` → `integrations/hermes/SOUL.md`

   It backs up replaced files and links as `*.bak-YYYYMMDDTHHMMSS-PID`;
3. copies `NYO_API_KEY` from the repo's `.env` into the profile's `.env` as `HERMES_CUSTOM_NYOLAB_API_KEY` if the profile has no key yet.

For an existing profile it refuses a different working checkout unless you
explicitly pass `--retarget`. To move deliberately, run
`bash integrations/hermes/install.sh --retarget` from the intended checkout.
It backs up `config.yaml` and updates only
`terminal.cwd` through Hermes, then relinks the skill and identity. Other profile
settings stay intact. Run it from your chosen checkout to avoid using one copy's
rules while the terminal runs another copy's code. Verify `pwd` in a new session.
Running it inside a named Hermes profile uses the same Hermes root; it does not
create a nested `profiles/clipper/profiles/clipper` directory.
Folder resolution also ignores `CDPATH`, which otherwise can print the path twice
and cause a malformed working folder. Temporary test checkouts cannot silently
retarget an existing profile.

Because of the links, a `git pull` updates the agent too. There's one copy of the rules.
All agents also read an optional git-ignored `CONTEXT.local.md` through `AGENTS.md`;
use it for pointers to private decisions and handoffs, not a second rules file.

## What stays in the profile (not in git)

- `config.yaml`: the model and paths. Reinstalling retargets only the working folder and keeps a backup. To change the model, edit it separately.
- `.env`: the key.
- Sessions and memory.

## Changing things

Change the skill, docs or code **in the repo**, then commit and push (see `AGENTS.md`).

## Windows

Hermes runs on macOS and Linux. On Windows, use OpenCode instead ([OPENCODE.md](OPENCODE.md)): it reads the same skill and rules.
