---
description: 🚀 SHIP — Pre-merge review → open PR
argument-hint: none
---

## Task

Take the current branch from "done" to an open PR: pre-merge review, then open the PR.
Orchestrator only: it chains existing commands and lets their own confirmations drive. The
repo has no CI or local gate, so there is no checks stage.

## Stage 1 — Pre-merge review (GATE)

Run `/ubot:start-pre-merge-review`. Read its final 🔴 count.
- Halted with unresolved 🔴 → ask (**AskUserQuestion**) *"Pre-merge review found unresolved
  critical issue(s). How do you want to proceed?"* (**Fix them first**, **Ship anyway**,
  **Abort**). Fix first / Abort → end with a one-line status.
- Fixed and continued → its fixes are uncommitted and the PR wouldn't contain them: ask
  *"The review left uncommitted fixes in N file(s). Commit them before opening the PR?"*
  (**Commit**, **Abort**). Commit → stage those files (explicit paths, never `*.pyc`),
  `fix(<scope>): <summary>`, then Stage 2.
- Passed → Stage 2.

## Stage 2 — Open the PR

`gh pr list --head "$(git branch --show-current)" --json number,url,state --limit 1`.
- OPEN PR exists → reuse it.
- Else run `/ubot:open-pr`. User aborts the push → end here.

## Stage 3 — Summary

```
## Ship summary — PR #<PR>

| Stage | Outcome |
|-------|---------|
| 1. Pre-merge review | ✅ passed / 🛠 fixed & committed / ⏭ shipped past criticals / 🛑 aborted |
| 2. Open PR          | 🔀 created / ♻️ reused / — not run |

**PR:** <url>
**In-game check owed:** <steps>
```

If Ship stopped early, still print where and why.
