---
description: 🔹 STAGED (pre-commit) — Generate a structured changelog and commit message from all git-staged changes
argument-hint: none
---

## Task

Generate a structured changelog from ALL git-staged changes, grouped by area, plus a commit
message. BRANCH version: `/ubot:changelog-branch`.

## Steps

### 1. Discover changes

Follow `.claude/review-shared/digest-discovery.md` (STAGED). Read
`.claude/review-shared/routing-tables.md` once for the area tags.

### 2. Categorize by area

Tag each meaningful change with its area. A change spanning areas gets an entry under each.

### 3. Write the changelog

**Title:** the dominant theme, under 80 chars.

**Entries:**

```
- **[AREA]** <Past-tense verb> `<symbol or path>` — <what it does, why it matters, key detail>
```

- Past tense: Added, Fixed, Expanded, Updated, Removed, Refactored.
- Specific: name the function, class, flag or file. No vague "improved X".
- Contextual: the why or the effect, not only the what.
- One `---` block per area, most impactful first.
- A changed `eXLib.mix`, a client-build/offset assumption, a new Saves format or a new
  hot-reloadable module gets its own bullet: they matter for anyone updating.

```markdown
## <Title>

---

- **[HUNT]** ...
---

---

- **[UI]** ...
---
```

## Output

Write `.claude/.tmp/changelog.md`, ending with `**Total: X changes across Y areas**`.

Then write `.claude/.tmp/commit-message.md`: `type(scope): summary` per
`.claude/review-shared/verify-and-commit.md` §Commits. Short body only when the why isn't
obvious.
