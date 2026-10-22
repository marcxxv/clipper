# Rules for AI agents in this repository

Read by OpenCode, Hermes (`clipper` profile), Claude Code and Codex.

**What this is:** a pipeline that turns videos into vertical captioned shorts for clipping campaigns. How to run it and the editorial rules: `.agents/skills/clipping/SKILL.md`. Details: `docs/HOW-IT-WORKS.md`.

**Who you're helping:** assume the user is not technical and is cost-conscious. Give short, plain answers, and state costs in money, e.g. "about 2 cents", not tokens.

## Private continuity
Read `CONTEXT.local.md` when it exists: it points to this user's private project
decisions, preferences and trial status. It is optional and git-ignored. Keep
personal context out of public docs; all agents use the same local file. Read the
current sources linked there before treating an older status as verified.

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
1. Update `README.md` / `docs/` if behaviour or settings changed. If a step, mode or flow changed, also update the diagram in `docs/architecture/*.d2` and run `bash docs/architecture/render.sh` (CI fails if the picture is out of date).
2. Update `.agents/skills/clipping/SKILL.md` if a rule or how-to changed. It's the only copy; every agent and the pipeline read it.
3. Add a dated entry to `CHANGELOG.md`.
4. Share it through git, automatically, as below.

A change that lives only in a chat is lost.

## Git: automatic, no need to ask

Before starting work, run `git pull` (if it fails because of local edits, keep them and tell the user in one line).

Who is working? Compare `gh api user --jq .login` with the repo owner (`gh repo view --json owner --jq .owner.login`):

**Owner:** after a change is tested, commit and `git push` to `main` right away. Use a clear message saying what changed and why.

**Anyone else:** `main` is protected; never try to push to it. This repository is public, so most people are not invited collaborators. Check `gh api repos/{owner}/{repo} --jq .permissions.push`:
- **`false` (a fork or a stranger):** keep every change local. Do not open a pull request unless the user asks for one.
- **`true` (an invited collaborator):** while doing the user's task, you may improve the shared pipeline: fix a bug, handle a new kind of video, make clips better for everyone. When that happens and the change is tested:
1. `git switch -c improve/<short-name>`, commit with a clear message;
2. `git push -u origin improve/<short-name>`;
3. `gh pr create --base main` with a short body: **what** changed, **why** (what went wrong or what's better), and **how it was tested** (commands run, results);
4. tell the user in one line, with the PR link. They don't need to understand git.

Do this without asking for small, clearly beneficial fixes. **Ask first** if the change is large (over ~200 changed lines), changes defaults, makes runs cost more, or removes a feature. Then switch back to `main` so the user's work continues normally.

**Never** open a pull request for personal settings (put those in `settings.local.json`, which is git-ignored), untested experiments, keys, or videos.

Pull requests run the `checks` workflow (Windows + Linux install and an offline test run). Check it with `gh pr checks`; fix it if it fails.

If `gh` isn't logged in, run `gh auth login` with the user, or leave the change local and explain in one line.

## Platform notes
- Windows: the Python is `pipeline\.venv\Scripts\python.exe`; macOS/Linux: `pipeline/.venv/bin/python`.
- Quote paths: video titles often contain spaces and symbols.
