---
description: 🔹 BRANCH (pre-merge) — Compare branch changes vs origin against README, RELEASE_NOTES, CLAUDE.md and docs/ and update stale documentation
argument-hint: "[base-branch]"
---

## Task

Check whether ALL changes on the current branch vs `origin/{base-branch}` (default
`origin/main`) leave any documentation stale: `CLAUDE.md`, `README.md`, `RELEASE_NOTES.md`,
`docs/*`, `.claude/review-shared/*.md`. Update the affected docs, after confirmation.
STAGED version: `/ubot:update-docs`.

A change that contradicts `CLAUDE.md` is either an intended design change (update the doc)
or a bug (fix the code). When unsure which side is wrong, flag it 🔴 and ask.

## Steps

1. **Discover changes:** `.claude/review-shared/digest-discovery.md` (BRANCH).
2. **Map to docs:** `.claude/review-shared/routing-tables.md` §Doc mapping + §Sync pairs.
   Also check: new modules missing from `CLAUDE.md` §Architecture and the routing area
   table; `_RAH_RELOAD_LIST` drift; user-visible changes missing from `RELEASE_NOTES.md`;
   README phase history.
3. **Read each mapped doc** and compare with what the code now does. Skip cosmetic changes.

## Findings format, confirmation and apply rules

Identical to `/ubot:update-docs` (🔴 MUST UPDATE / 🟡 WORTH MENTIONING / 🔵 MINOR; ask
"Apply these documentation updates? (yes / no / pick)" before editing; keep each doc's
structure and voice; don't remove correct content).

Zero findings: `✅ No documentation updates needed — docs are in sync with this branch.`

## Output

`✅ No documentation updates needed — X docs checked.` or
`📝 Applied N updates across M docs.` + one line per doc.
