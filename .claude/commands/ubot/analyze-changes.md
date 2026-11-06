---
description: 🔹 STAGED (pre-commit) — Read all staged changes once and write a shared digest for downstream review commands
argument-hint: none
---

## Task

Read every git-staged change **once** and write a compact digest that `/ubot:code-review`,
`/ubot:update-docs` and `/ubot:changelog` reuse instead of each re-running
`git diff --cached` and re-reading every file.

## Steps

### 1. Discover changes

```bash
git diff --cached --name-status
git diff --cached --stat
git diff --cached
git diff --cached --binary | git hash-object --stdin   # fingerprint
```

If nothing is staged, say so and stop.

### 2. Read every changed file

Read every staged file in full, applying the skip list in
`.claude/review-shared/digest-discovery.md` (`*.pyc` ignored, binaries stat-only, a changed
`eXLib.mix` called out).

### 3. Write the digest

Read `.claude/review-shared/routing-tables.md` once. Write `.claude/.tmp/change-analysis.md`
(create `.claude/.tmp/` if missing):

~~~markdown
# Staged analysis

**Fingerprint:** <hash-object output>
**Files changed:** N files (+X −Y lines)

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
- **Sync pairs triggered:** <list, and whether the other side is also staged>
- **Docs to read before reviewing:** <deduplicated>
```

## Output

`📝 Digest written to .claude/.tmp/change-analysis.md — N files analyzed.`

Don't print the digest; it's for the downstream commands.
