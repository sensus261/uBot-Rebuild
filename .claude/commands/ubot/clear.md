---
description: Reset the review-pipeline session state and re-anchor on project ground truth
argument-hint: none
---

## Task

1. Drop every assumption from earlier in this session about staged changes, digests or review
   findings; they may be stale. Re-derive from `git status` and fresh digests when needed.
2. Delete stale pipeline state:
   ```bash
   rm -f .claude/.tmp/change-analysis.md .claude/.tmp/branch-analysis.md
   ```
   Keep changelogs, commit messages and release notes.
3. Re-anchor: conventions are in `CLAUDE.md`; before working on an area, read its docs per
   `.claude/review-shared/routing-tables.md` §Doc mapping. Don't rely on memory alone.

Confirm with: `🧹 Session context reset — digests cleared.`
