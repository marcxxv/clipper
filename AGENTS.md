# Rules for AI agents in this repository

Read by OpenCode, Hermes (`clipper` profile), Claude Code and Codex.

**What this is:** a pipeline that turns videos into vertical captioned shorts for clipping campaigns. How to run it and the editorial rules: `.agents/skills/clipping/SKILL.md`. Details: `docs/HOW-IT-WORKS.md`.

**Who you're helping:** assume the user is not technical and is cost-conscious. Give short, plain answers, and state costs in money, e.g. "about 2 cents", not tokens.

## Do
- Run the pipeline (`pipeline/clips.py`, `pipeline/reedit.py`) rather than editing video by hand.
- Put inputs in `sources/`; results land in `output/<video>/`. Keep this layout.
- After a run, read `report.md` and look at real frames before calling a clip good. Lines starting with `!` in the run output are problems; deal with them.
- Set clip length from the campaign brief when the user mentions one.
- If setup looks broken, run `clips.py --check` first.

## Never without the user's explicit OK
- Post or upload anything to TikTok, Instagram, YouTube, X or Whop.
- Use footage the user doesn't own and no campaign has licensed.
- Spend more than about 10 US cents in one task, or switch to a more expensive model.
- Delete anything in `output/` or `sources/`.
- Commit or print `.env` or any key.

## Keeping records (every change to code, settings, rules or docs)
1. Commit (or branch) before editing, so it can be undone.
2. Update `README.md` / `docs/` if behaviour or settings changed.
3. Update `.agents/skills/clipping/SKILL.md` if a rule or how-to changed. It's the only copy; every agent and the pipeline read it.
4. Add a dated entry to `CHANGELOG.md`, then commit with a clear message and push.

A change that lives only in a chat is lost.

## Platform notes
- Windows: the Python is `pipeline\.venv\Scripts\python.exe`; macOS/Linux: `pipeline/.venv/bin/python`.
- Quote paths: video titles often contain spaces and symbols.
