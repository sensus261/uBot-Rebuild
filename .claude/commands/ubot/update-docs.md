---
description: 🔹 STAGED (pre-commit) — Compare git-staged changes against README, RELEASE_NOTES, CLAUDE.md and docs/ and update stale documentation
argument-hint: none
---

## Task

Check whether ALL git-staged changes leave any documentation stale: `CLAUDE.md`,
`README.md`, `RELEASE_NOTES.md`, `docs/*`, `.claude/review-shared/*.md`. Update the affected
docs, after confirmation. BRANCH version: `/ubot:update-docs-branch`.

`CLAUDE.md` is the project spec for how the code is structured and what its conventions are.
A change that contradicts it is either an intended design change (update the doc) or a bug
(fix the code). When unsure which side is wrong, flag it 🔴 and ask.

## Steps

1. **Discover changes:** `.claude/review-shared/digest-discovery.md` (STAGED). The digest's
   "Docs" and "Sync pairs" fields are the starting point.
2. **Map to docs:** `.claude/review-shared/routing-tables.md` §Doc mapping + §Sync pairs.
   Also check: new modules missing from `CLAUDE.md` §Architecture and the routing area
   table; `_RAH_RELOAD_LIST` drift; user-visible changes missing from `RELEASE_NOTES.md`.
3. **Read each mapped doc** and compare with what the code now does. Skip cosmetic changes.

## Findings format

```
## <doc path> §<section>

### 🔴 MUST UPDATE — behavior mismatch
- Doc says: <claim>
- Code does: <behavior>
- Update: <change>

### 🟡 WORTH MENTIONING — new behavior, flag, module or convention
- New: <thing>
- Add to doc: <suggested content>

### 🔵 MINOR — stale reference (path, name, count)
- <detail>
```

Zero findings: `✅ No documentation updates needed — docs are in sync with staged changes.`

## Confirm, then apply

Ask: "Apply these documentation updates? (yes / no / pick)". Wait for the answer.

For each approved update:
- Read the whole doc first; keep its structure, voice and density.
- Don't remove content unless it's wrong.
- Repo-relative paths and backticked symbols.
- `CLAUDE.md` stays minimal: add only what future sessions need on every prompt.

## Output

`✅ No documentation updates needed — X docs checked.` or
`📝 Applied N updates across M docs.` + one line per doc.
