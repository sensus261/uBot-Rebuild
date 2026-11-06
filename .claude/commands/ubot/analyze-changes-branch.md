---
description: 🔹 BRANCH (pre-merge) — Read all branch changes vs origin once and write a shared digest for downstream review commands
argument-hint: "[base-branch]"
---

## Task

Read every change on the current branch vs `origin/{base-branch}` (default `origin/main`)
**once** and write a compact digest that `/ubot:code-review-branch`,
`/ubot:update-docs-branch` and `/ubot:changelog-branch` reuse instead of each re-diffing and
re-reading every file.

## Steps

### 1. Discover changes

```bash
BASE="${1:-main}"
git fetch origin "$BASE" -q
git diff --name-status "origin/$BASE"...HEAD
git log --oneline "origin/$BASE"...HEAD
git diff --stat "origin/$BASE"...HEAD
git diff "origin/$BASE"...HEAD
echo "$(git rev-parse "origin/$BASE") $(git rev-parse HEAD)"   # fingerprint
git status --short                                             # uncommitted leftovers
```

No commits ahead of `origin/$BASE` → say so and stop.

### 2. Read every changed file

Read every changed file in full, applying the skip list in
`.claude/review-shared/digest-discovery.md`.

### 3. Write the digest

Read `.claude/review-shared/routing-tables.md` once. Write `.claude/.tmp/branch-analysis.md`
(create `.claude/.tmp/` if missing):

~~~markdown
# Branch analysis: `<branch>` vs `origin/<base>`

**Fingerprint:** <origin sha> <head sha>
**Commits:** N
**Files changed:** N files (+X −Y lines)
**Uncommitted (not analyzed):** <git status --short summary ignoring *.pyc, or "none">

## <file-path>

- **Change type:** added / modified / deleted / renamed
- **Lines:** +X −Y
- **Area:** [HUNT] / [UI] / … (routing-tables §Area tags)
- **Docs:** <doc + section from §Doc mapping, or "none">
- **Sync pairs:** <rows of §Sync pairs this file triggers, or "none">
- **Summary:** <new/changed functions and classes, eXLib calls added, flags, hot-reload impact>
- **Relevant diff:**
  ```diff
  <changed hunks with a few lines of context, not the whole file>
  ```
~~~

End with:

```markdown
## Overview

- **Total files changed:** N
- **By area:** [HUNT] x, [UI] x, …
- **Sync pairs triggered:** <list, and whether the other side also changed>
- **Docs to read before reviewing:** <deduplicated>
```

## Output

`📝 Digest written to .claude/.tmp/branch-analysis.md — N files analyzed against origin/<base>.`

Don't print the digest; it's for the downstream commands.
