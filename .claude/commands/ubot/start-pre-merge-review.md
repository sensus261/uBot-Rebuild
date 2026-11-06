---
description: 🔹 BRANCH (pre-merge) — Pre-merge pipeline: analyze → code review → docs → changelog → report (optionally posted on the PR)
argument-hint: "[base-branch]"
---

## Task

Run the pre-merge pipeline over the current branch vs `origin/{base-branch}` (default
`origin/main`). Orchestrator only: it invokes the BRANCH commands in order (passing
`[base-branch]` along), with one gate on the code review. Run the stages sequentially; stop
only at the gate. STAGED equivalent: `/ubot:start-pre-commit-review`.

No test/lint stage: the repo has none. See `.claude/review-shared/verify-and-commit.md`.

## Pipeline

### Stage 0 — Analyze

1. Run `/ubot:analyze-changes-branch`; confirm it wrote `.claude/.tmp/branch-analysis.md`.
2. Read `.claude/review-shared/routing-tables.md` and the doc sections in the digest's
   "Docs to read" list, once.

### Stage 1 — Code review (GATE)

Run `/ubot:code-review-branch`. Read the 🔴 count.
- **0:** Stage 2.
- **> 0:** ask (**AskUserQuestion**) *"Code review found N critical issue(s). How do you want
  to proceed?"*:
  - **Fix and halt** → fix the 🔴 findings only, syntax-check the fixed files, then **HALT**:
    *Fixes applied. Commit, push, and re-run `/ubot:start-pre-merge-review`.*
  - **Fix and continue** → the same fix and check; the fixes stay uncommitted (never commit
    unasked), so later stages must cover them on top of the branch (`git diff -- <files>`).
    Keep a list of fixed files and findings.
  - **Skip** → Stage 2, findings left as they are.

### Stage 2 — Docs sync (no halt)

Run `/ubot:update-docs-branch`; let its confirmation run; continue.

### Stage 3 — Changelog

Run `/ubot:changelog-branch` (writes `.claude/.tmp/changelog-branch.md`).

### Stage 4 — Report

Write `PRE-MERGE-REVIEW-REPORT.md` at the repo root (overwrite; gitignored): per stage
whether it ran, its verdict, findings, where and why a gate halted, fixed vs skipped
findings, uncommitted fix files, artifact paths, and the in-game checks still owed.

### Cleanup

```bash
rm -f .claude/.tmp/branch-analysis.md
```

## Final summary

```
## Pre-merge pipeline summary — `<branch>` vs `origin/<base>`

| Stage | Outcome |
|-------|---------|
| 0. Analyze     | 📝 digest written |
| 1. Code review | ✅ passed / 🛠 fixed (halted) / 🛠 fixed, continued / ⏭ skipped criticals |
| 2. Docs sync   | 📝 updated / ✅ in sync / — not run |
| 3. Changelog   | 📄 written / — not run |
| 4. Report      | 📄 written |

**Changelog:** .claude/.tmp/changelog-branch.md
**Report:** PRE-MERGE-REVIEW-REPORT.md
**Uncommitted fixes:** <files> — commit and push before merging   (only after "Fix and continue")
**In-game check owed:** <what to deploy/reload and exercise>
```

If the gate halted, mark later stages "— not run", repeat the re-run note, and still write
the report.

## Last step — Publish the report on the PR (ask)

Skip when the gate halted. Find an open PR:

```bash
gh pr list --head "$(git branch --show-current)" --state open --json number,url --limit 1
```

- **None** → *"No open PR for `<branch>`: the report stays local."*
- **Found** → ask *"Publish the pre-merge report as a comment on PR #<N> (<url>)?"*
  (**Yes**, **No**). Posting is outward-facing: never without a **Yes**.
  **Yes** → `gh pr comment <N> --body-file <file>` where the file is
  `PRE-MERGE-REVIEW-REPORT.md` plus a final line
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Reply with the comment
  URL. If the report mentions uncommitted fixes, say the PR doesn't contain them until pushed.
