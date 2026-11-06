---
description: 🔹 STAGED (pre-commit) — Pre-commit pipeline: analyze → code review → docs → changelog
argument-hint: none
---

## Task

Run the pre-commit pipeline over the **git-staged** changes. Orchestrator only: it invokes
the STAGED commands in order, with one gate on the code review. Run the stages sequentially;
stop only at the gate. BRANCH equivalent: `/ubot:start-pre-merge-review`.

There is no test or lint stage (the repo has neither); the syntax check and the in-game
steps are in `.claude/review-shared/verify-and-commit.md`.

## Pipeline

### Stage 0 — Analyze

1. Run `/ubot:analyze-changes`; confirm it wrote `.claude/.tmp/change-analysis.md`.
2. Read `.claude/review-shared/routing-tables.md` and the doc sections in the digest's
   "Docs to read" list, once. Every later stage reuses them.

### Stage 1 — Code review (GATE)

Run `/ubot:code-review`. Read the 🔴 Critical count.
- **0:** Stage 2.
- **> 0:** ask (**AskUserQuestion**) *"Code review found N critical issue(s). How do you want
  to proceed?"*:
  - **Fix and halt** → fix the 🔴 findings only, run the Py2.7 syntax check on the fixed
    files (`verify-and-commit.md`), then **HALT**: *Fixes applied. Re-stage and re-run
    `/ubot:start-pre-commit-review`.*
  - **Fix and continue** → the same fix and check, then stage the fixed files (explicit
    paths, never `*.pyc`); a fixed file with unrelated unstaged changes → ask first. Refresh
    the digest entries and **Fingerprint** (`git diff --cached --binary | git hash-object
    --stdin`), then Stage 2.
  - **Skip** → Stage 2, findings left as they are.

### Stage 2 — Docs sync (no halt)

Run `/ubot:update-docs`; let its confirmation run; continue.

### Stage 3 — Changelog + commit message

Run `/ubot:changelog` (writes `.claude/.tmp/changelog.md` and `.claude/.tmp/commit-message.md`).

### Stage 4 — Report

Write `PRE-COMMIT-REVIEW-REPORT.md` at the repo root (overwrite; gitignored): per stage
whether it ran, its verdict, findings (counts), docs changed, fixed vs skipped, files a fix
staged, artifact paths, and what to verify in-game.

### Cleanup

```bash
rm -f .claude/.tmp/change-analysis.md
```

## Final summary

```
## Pre-commit pipeline summary

| Stage | Outcome |
|-------|---------|
| 0. Analyze     | 📝 digest written |
| 1. Code review | ✅ passed / 🛠 fixed (halted) / 🛠 fixed, continued / ⏭ skipped criticals |
| 2. Docs sync   | 📝 updated / ✅ in sync / — not run |
| 3. Changelog   | 📄 written / — not run |
| 4. Report      | 📄 written |

**Commit message:** .claude/.tmp/commit-message.md
**In-game check:** <what to deploy/reload and exercise>
```

If the gate halted the pipeline, mark later stages "— not run", repeat the re-run note, and
still write the report.
