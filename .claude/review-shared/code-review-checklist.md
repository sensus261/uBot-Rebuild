# Code review checklist

There is no test suite and no linter: the review is the safety net, and final verification is
in-game. Apply every section that touches the changed areas. `CLAUDE.md` is the spec; a
mismatch between code and doc is a finding either way (bug or stale doc).

## Severity

- 🔴 **Critical**: crash or hang inside the game process, a break of startup (`init.py`
  phases), Python 3 syntax in a Py2.7 file, a CLAUDE.md convention that silently breaks
  behavior (NaN positions), a committed debug flag left `True` that spams chat, or a change
  that trusts/loads something unreviewed (new binary, network fetch, `exec` of external data).
- 🟡 **Warning**: hot-reload unsafe, missing guard, sync-pair miss, weak error handling,
  duplicated logic that already exists in `OpenLib`.
- 🔵 **Info**: docs impact, simplification, naming.

## 1. Python 2.7 compatibility

- No Python 3 only syntax: f-strings, `print()` with `sep=`/`end=`, `nonlocal`, type hints,
  `yield from`, `async`, keyword-only args, `except X as e` is fine in 2.7 but `raise ... from` is not.
- `print` statements are normal here; don't "modernize". `dict.iteritems()` is fine.
- Integer division: `/` on ints truncates in Py2; check distance, pixel and tile math.
- `str` vs `unicode`: client text may be a byte string in a legacy codepage; check
  concatenation and `.encode`/`.decode` of chat/item names.
- Mixed tabs and spaces: match the file's existing indentation (some files use tabs).

## 2. Game-process safety

- Anything slow or blocking (loops without sleep, long A* on the UI thread) freezes the
  client. Long work goes through the existing timer/thread helpers (`OpenThreads`, the
  per-frame update pattern used by the module), with an exit condition.
- Exceptions inside a game callback can kill the hook or spam the log: wrap new callbacks
  and handle failure by stopping the bot cleanly, not by raising.
- Never block waiting for a server reply.
- Packet sending is **disabled** in the DLL. New code that depends on `eXLib` send-side
  calls is dormant: flag it 🟡 and make sure it fails soft.

## 3. Client / eXLib conventions (CLAUDE.md)

- Positions: `eXLib.GetPixelPosition`, never `chr.GetPixelPosition` (NaN on 26.1.11).
  Distance math guards against NaN.
- Client modules (`chr`, `net`, `player`, `chat`, `app`, ...) come from the resolved
  handles (Hooks/`init.py` signature scan), not a fresh `import chr` / `import net`.
- Any new `eXLib.*` function actually exists in the shipped `eXLib.mix` for the client
  build. Offsets/signatures are build-specific.
- Movement goes through `OpenLib` helpers (`GoToPositionAvoidingObjects`, `StopMovement`),
  keeping the manual-intervention-stops-path behavior.

## 4. Hot-reload safety (modules in `_RAH_RELOAD_LIST`)

- The module bottom rebinds the live singleton's class instead of creating a second
  instance or window.
- Module-level state that must survive `reload()` is not re-initialised unconditionally.
- No new timers/threads/hooks registered at import time without being torn down or guarded
  against double registration.
- A new hot-reloadable module is added to `_RAH_RELOAD_LIST` (and `/rah-ui` list when it
  has `_rebuildWindow`).
- `init.py` itself is never reloaded: the `/rah` hook lives there on purpose.

## 5. Startup (`init.py`, two phases)

- Phase-guarded by `sys._ubot_init_phase2`; the file runs twice. Names shared across both
  halves are intentional. Check nothing moved between phases accidentally.
- The game-phase callback replay still happens before `ActionBot`/`Data` need it.

## 6. UI

- Widgets go through `UIComponents` wrappers where one exists.
- `BuildWindow` / layout edits keep working with `/rah-ui` (windows rebuild in place).
- Image paths exist under `OpenBot/Images/`.

## 7. Config and saves

- Files under `OpenBot/Saves/` are user data: loaders tolerate missing/old keys and bad
  JSON; the code never overwrites a user's config with defaults silently.
- `.action` files keep the format `ActionBot` parses.

## 8. Debug flags and logging

- `AH_DEBUG`, `EB_DEBUG`, `DEBUG` (ShopSearcher), `STATUS_DEBUG`, `PHASE1_DEBUG`,
  `MANUAL_STOP_DEBUG` are `False` in committed code.
- No stray `print`/chat spam, no commented-out blocks, no dead code.

## 9. Safety and trust

- No new dependency on an unreviewed binary; a changed `eXLib.mix` is called out.
- No code that exfiltrates data (network calls, writes outside the game dir) or loads remote code.
- `ubot-deploy.ps1`: never touches files while the client runs unless `-Force`; keeps the
  `*.ubot-backup` behavior; `-WhatIf` still honored.

## 10. Style

- Reads like the surrounding file: naming, comment density, tabs vs spaces.
- Comments in English.

## 11. Branch only

- Commit messages follow `type(scope): summary` and match what the commits do.
- No fixup noise that should be squashed before merge (only flag it; never rewrite history).
- Tracked `*.pyc` modifications riding along in the diff are noise: mention once that they
  should not be committed.
