---
description: 📝 PRD — Plan a feature collaboratively, write a PRD .md at the repo root, optionally open a GitHub issue
argument-hint: "[feature-description]"
---

## Task

Turn a raw idea into a PRD through real, round-by-round collaboration, write it to
`PRD-<slug>.md` at the repo root (gitignored, untracked), then optionally open a GitHub
issue from it. Never draft the whole thing silently: propose each round and let the user
react before moving on.

## Stage 0 — Seed

`$ARGUMENTS` non-empty → reflect the idea back briefly to confirm. Empty → ask *"What
feature or change do you want to plan?"* and wait.

## Stage 1 — Rounds

1. **Context:** what's broken or missing, why it matters. Propose a paragraph; confirm.
2. **Goals / Non-goals:** propose goals; explicitly ask what's out of scope. Check the idea
   against `CLAUDE.md` and the README phase plan. Raise at once: anything that needs the
   disabled send-side packet layer, a new `eXLib` export (which means a change in the DLL
   repo, not here), or a new client-build-specific offset.
3. **Implementation plan:** read the relevant code and owning docs first
   (`.claude/review-shared/routing-tables.md` §Doc mapping; `Explore` agent for broad
   searches). Propose phases with real file paths: the module(s), UI (`UIComponents`,
   `BuildWindow`), Saves format, `init.py` wiring, whether it joins `_RAH_RELOAD_LIST`. Add
   **"Docs to update"**. Get sign-off.
4. **Verification:** no tests exist, so spell out the manual in-game steps per phase
   (`ubot-deploy.ps1` command, `/rah` or `/rah-ui`, what to click, what chat/log shows) and
   the Py2.7 syntax check.

## Stage 2 — Write

1. Slug = kebab-case title, ~50 chars. Tell the user the filename before writing.
2. Write `PRD-<slug>.md` with Context, Goals / Non-goals, Implementation plan, Verification,
   Docs to update. Don't `git add` it.

## Stage 3 — Optional issue

Never open one unprompted. Ask *"PRD written to `PRD-<slug>.md`. Create a GitHub issue from
it?"* (**Yes**, **Keep it local only**).

Yes → ask for the **title** (default: PRD title) and **labels** from `gh label list` (never
invent), then
`gh issue create --title "<title>" --body-file PRD-<slug>.md --label <l1> ...`. Show the
issue number and URL; suggest a branch named `issue-<num>-<slug>`.

## Stage 4 — Summary

PRD path, issue URL (if created), suggested next step.
