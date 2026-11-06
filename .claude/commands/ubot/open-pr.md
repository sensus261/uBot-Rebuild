---
description: 🔀 PR — Push the current branch and open a PR against main with a generated title/body
argument-hint: none
---

## Task

Push the current branch and open a PR against `main`, with title and body generated from the
branch changelog. Never push or open a PR without the user's confirmation. Never `--force`.
Base is always `main`.

Related: `/ubot:ship` (review → PR), `/ubot:pr-review-feedback` (read a reviewer's feedback).

## Stage 0 — Preconditions

1. `BRANCH="$(git branch --show-current)"`.
2. On `main` → STOP and ask (**AskUserQuestion**): *"You're on `main`. Create a feature
   branch first, or abort?"* (**Create a branch**, **Abort**). Create → ask for a name
   (suggest `<type>/<slug>`), `git switch -c <name>`.
3. `gh pr list --head "$BRANCH" --json number,url,state --limit 1`. An OPEN PR exists → show
   it and STOP.

## Stage 1 — Confirm and push

1. Show what goes in:
   ```bash
   git fetch origin main -q
   git log --oneline origin/main..HEAD
   git status --short
   ```
2. Uncommitted changes other than `*.pyc` → STOP; tell the user to commit first
   (`.claude/review-shared/verify-and-commit.md` §Commits). Don't commit for them. Modified
   tracked `*.pyc` files are noise: remind the user not to commit them.
3. No commits ahead of `origin/main` → STOP; nothing to open.
4. Ask *"Push `<BRANCH>` to origin and open a PR against `main`?"* (**Yes, push & open**,
   **Abort**).
5. Yes → `git push -u origin HEAD`.

## Stage 2 — Title and body

1. Run `/ubot:changelog-branch` (writes `.claude/.tmp/changelog-branch.md`).
2. **Title:** its `type(scope): summary` title (< 80 chars).
3. **Body** (template in `verify-and-commit.md` §Commits): What (one line), Why, Changes (the
   changelog bullets by area), Test plan (deploy + in-game steps; state plainly what was not
   run in-game). End with the session's required attribution line.
4. Branch name encodes an issue (`issue-<n>-…`) → ask *"Add `Closes #<n>`?"* (**Yes**, **No**).

## Stage 3 — Create and report

Ask *"Open as-is, or add labels/reviewers?"* (**Open as-is**, **Add labels/reviewers**);
labels only from `gh label list`.

```bash
gh pr create --base main --title "<title>" --body-file .claude/.tmp/pr-body.md
```

(Write the body to `.claude/.tmp/pr-body.md` first.) Print the PR URL.
