---
description: 🏷️ RELEASE — Summarize commits since the last tag, propose a semver version, and publish a git tag + GitHub release
argument-hint: "[version]"
---

## Task

Cut a GitHub release from `main`: gather everything since the last tag, draft release notes,
propose a version, and after the user confirms, tag, push and publish.

Conventions: tags are lightweight `vX.Y.Z` (`git tag <v>`, no `-a`/`-m`); notes live in the
GitHub Release. Mirror notable entries into `RELEASE_NOTES.md` only if the user asks. No
emoji in the release body.

## 0. Preflight (abort with a clear message; never auto-fix)

- Current branch is `main`; `git status --porcelain` is empty apart from `*.pyc` noise
  (mention it, don't touch it).
- `git fetch origin main --tags`.
- Behind `origin/main` → tell the user to pull. Ahead → note it; Step 6 pushes `main` first.

## 1. Range

```bash
LAST_TAG=$(git for-each-ref --sort=-creatordate --format='%(refname:short)' refs/tags | head -1)
```

- No tag yet: whole history in scope; say how many commits before continuing.
- Else `git log "$LAST_TAG"..HEAD --oneline`; empty → "Nothing to release since $LAST_TAG."

## 2. Discover

As the BRANCH fallback in `.claude/review-shared/digest-discovery.md`, with `$LAST_TAG` (or
the root commit) as the base. Include `README.md`, `RELEASE_NOTES.md`, `docs/` changes as
`[DOCS]` bullets. Large ranges: key sections only.

## 3. Draft the notes

Area tags from `.claude/review-shared/routing-tables.md`.

```
- **[AREA]** <Past-tense verb> `<symbol or path>` — <what, why, key detail>
```

Add an **Install / update notes** section whenever the range changes `eXLib.mix`, the
supported client build, `init.py` startup, Saves formats, or `ubot-deploy.ps1` (the steps:
close the client, `.\ubot-deploy.ps1 Install`, anything to delete or reconfigure). Write the
notes to `.claude/.tmp/release-notes.md`, ending with `**Total: X changes across Y areas**`.

## 4. Propose a version

- `!:` or `BREAKING CHANGE` → major. Any `feat` → minor. Else patch.
- Pre-1.0 (`v0.x`): breaking → minor, everything else → patch.
- An explicit `[version]` argument replaces the proposal (still confirmed below).

## 5. Confirm (GATE)

Show the full notes. **AskUserQuestion**: *"Which version should this release be tagged
as?"* First option the proposal (Recommended); Other for custom. This single answer
authorizes Step 6.

## 6. Publish

```bash
git push origin main                 # only if local main was ahead
git tag <version>
git push origin <version>
gh release create <version> --title "<version>" --notes-file .claude/.tmp/release-notes.md
```

Note: attaching `eXLib.mix` or a zip to the release is out of scope unless the user asks.

## Output

```
**Tagged <version>** — X commits since <LAST_TAG>, Y changes across Z areas
<release URL>
```
