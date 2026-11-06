---
description: 🔹 BRANCH (pre-merge) — Generate a structured changelog from all changes on the current branch vs origin (for PR bodies)
argument-hint: "[base-branch]"
---

## Task

Generate a structured changelog from ALL changes on the current branch vs
`origin/{base-branch}` (default `origin/main`), grouped by area. Used for PR bodies.
STAGED version: `/ubot:changelog`.

## Steps

### 1. Discover changes

Follow `.claude/review-shared/digest-discovery.md` (BRANCH; the fallback also lists commit
subjects). Read `.claude/review-shared/routing-tables.md` once for the area tags.

### 2. Categorize by area

Tag each meaningful change with its area. A change spanning areas gets an entry under each.

### 3. Write the changelog

**Title:** the dominant theme of the branch, under 80 chars, in `type(scope): summary` form
so `/ubot:open-pr` can reuse it.

**Entries:**

```
- **[AREA]** <Past-tense verb> `<symbol or path>` — <what it does, why it matters, key detail>
```

Same rules as `/ubot:changelog`: past tense, specific, contextual, one `---` block per area,
and own bullets for `eXLib.mix` changes, client-build assumptions, Saves-format changes and
new hot-reloadable modules.

## Output

Write `.claude/.tmp/changelog-branch.md`, ending with `**Total: X changes across Y areas**`.
Revisions update the same file.
