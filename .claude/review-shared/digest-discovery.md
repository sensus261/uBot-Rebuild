# Digest-first discovery

Review commands read one shared digest instead of each re-diffing and re-reading every file.

| Variant | Scope | Digest | Written by |
|---|---|---|---|
| STAGED | `git diff --cached` | `.claude/.tmp/change-analysis.md` | `/ubot:analyze-changes` |
| BRANCH | `origin/$BASE...HEAD` (`BASE` = first arg, default `main`) | `.claude/.tmp/branch-analysis.md` | `/ubot:analyze-changes-branch` |

## 1. Use the digest when it's fresh

Each digest's header records a fingerprint. Recompute it and compare:

```bash
# STAGED
git diff --cached --binary | git hash-object --stdin
# BRANCH
git fetch origin "$BASE" -q
echo "$(git rev-parse "origin/$BASE") $(git rev-parse HEAD)"
```

Match: work from the digest's per-file summaries and hunks. Open a source file only when the
digest can't answer the question (surrounding context, callers).
Missing or mismatched: use the fallback. A stale digest is never used.

## 2. Fallback

```bash
# STAGED
git diff --cached --name-status
git diff --cached --stat
git diff --cached

# BRANCH
git fetch origin "$BASE" -q
git diff --name-status "origin/$BASE"...HEAD
git log --oneline "origin/$BASE"...HEAD
git diff --stat "origin/$BASE"...HEAD
git diff "origin/$BASE"...HEAD
```

Then read the changed files, applying the skip list. With more than ~15 changed files, run
the matching analyze command first so the following commands reuse its digest.

## Skip list

- Compiled `*.pyc` (gitignored, but some old ones are still tracked and show up as modified
  after every game run): ignore them completely, they are never a finding.
- Binary assets: `OpenBot/Images/*.tga`, `OpenBot/Maps/*.dat`: stat only; note additions.
- `eXLib.mix` (prebuilt DLL): stat only, but **say loudly** when it changed (it is an
  unreviewed binary, see `docs/ISSUE-safety-concerns.md`).
- Vendored `OpenBot/lib/*`: stat only unless the task is about them.
- `.claude/` files: skip unless the task is about docs or commands.
- **Never skip** `init.py`, `ubot-deploy.ps1`, `OpenBot/Saves/Actions/*.action` or anything
  under `OpenBot/Modules/`: they are behavior.

## Scope notes

- BRANCH covers committed work only. If `git status --short` shows uncommitted changes
  (other than `*.pyc`), say so in the output; they are not reviewed.
- STAGED covers the index only. Mention unstaged changes to the same files if present.
