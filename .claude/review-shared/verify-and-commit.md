# Verification and commits

## No automated gate

uBot has no build, linter or test suite; the code only runs inside the live client. The
"gate" is therefore:

1. **Syntax check** of every changed `.py` file with a Python 2.7 interpreter when one is
   available (`py -2 -m py_compile <file>` or `python2 -m py_compile <file>`); delete the
   `.pyc` it produces if it was untracked. No Py2 available → say the syntax was only
   reviewed by eye, never claim it compiled.
2. **Read-through** for the Py2.7 / eXLib / hot-reload rules in
   `code-review-checklist.md`.
3. **In-game verification** by the user. Hand over exactly what to do:
   - `.\ubot-deploy.ps1 Status` then `Install` (add `-WhatIf` first if unsure; the script
     refuses while the client runs unless `-Force`).
   - Already injected: `/rah` in game chat reloads the hot-reloadable modules; `/rah-ui`
     also rebuilds their windows (needed after `BuildWindow` / layout edits).
   - Name the module, the button/command to exercise, and what the chat/log should show.
4. Never claim a change "works" from reading alone; say "not run in-game".

## Commits and PRs

- `type(scope): summary`; type ∈ feat, fix, refactor, perf, docs, chore; scope = lowercase
  area from `routing-tables.md` (`hunt`, `shop`, `move`, `ui`, `boot`, `deploy`, `dll`, ...).
  Multi-area: the dominant scope, or join summaries with `&&`.
- Stage explicit paths; never `git add .` / `-A`. **Never stage `*.pyc`.** Never `--force`,
  never rewrite pushed history, never push without the user's explicit yes.
- End messages and PR bodies with whatever attribution lines the session requires.
- PR body:

  ```markdown
  ## What
  ## Why
  ## Changes
  ## Test plan      <!-- deploy + in-game steps; say what was NOT run in-game -->
  ```
