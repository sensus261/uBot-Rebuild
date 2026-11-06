---
description: 🔹 BRANCH (pre-merge) — Code review of all changes on the current branch vs origin for Py2.7/eXLib correctness, hot-reload safety, conventions and doc sync
argument-hint: "[base-branch]"
---

## Task

Review ALL changes on the current branch vs `origin/{base-branch}` (default `origin/main`)
for correctness, CLAUDE.md conventions and completeness. Report findings by severity. Don't
apply fixes unless the user asks. STAGED version: `/ubot:code-review`.

## Steps

1. **Discover changes:** `.claude/review-shared/digest-discovery.md` (BRANCH). Uncommitted
   changes are not reviewed; mention them.
2. **Load context:** read `.claude/review-shared/routing-tables.md` once, then the doc
   sections mapped to the changed areas. Only those.
3. **Review:** apply `.claude/review-shared/code-review-checklist.md`, including §Branch
   only (commit messages, stray tracked `*.pyc`). Open callers and surrounding code where
   the diff alone can't prove correctness; say what should be checked in-game.

## Output

```
## <file-path>

### 🔴 Critical (crash / hang / startup break / convention that silently breaks behavior)
- Line N: <problem>. <fix>.

### 🟡 Warning (hot-reload / sync pair / error handling / duplication)
- Line N: <problem>. <fix>.

### 🔵 Info (docs impact / simplification)
- <note>.
```

End with the severity count table (🔴 / 🟡 / 🔵) and "None found." for an empty severity.
