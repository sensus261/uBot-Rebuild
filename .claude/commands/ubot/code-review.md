---
description: 🔹 STAGED (pre-commit) — Code review of all git-staged files for Py2.7/eXLib correctness, hot-reload safety, conventions and doc sync
argument-hint: none
---

## Task

Review ALL git-staged files for correctness, CLAUDE.md conventions and completeness. Report
findings by severity. Don't apply fixes unless the user asks. BRANCH version:
`/ubot:code-review-branch`.

## Steps

1. **Discover changes:** `.claude/review-shared/digest-discovery.md` (STAGED).
2. **Load context:** read `.claude/review-shared/routing-tables.md` once, then the doc
   sections mapped to the changed areas (the digest's "Docs to read" list). Only those.
3. **Review:** apply `.claude/review-shared/code-review-checklist.md`. Open callers and
   surrounding code where the diff alone can't prove correctness. There are no tests to lean
   on, so reason about the in-game behavior and say what should be checked in-game.

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

End with:

| Severity | Count |
|----------|-------|
| 🔴 Critical | N |
| 🟡 Warning | N |
| 🔵 Info | N |

Write "None found." for an empty severity.
