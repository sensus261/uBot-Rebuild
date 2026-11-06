# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

uBot / OpenBot for the GameForge Metin2 client (`metin2client.exe`, 32-bit). It is a **Python 2.7** bot layer that runs *inside the game process* on top of `eXLib.mix`, a prebuilt native DLL that exposes game functions (movement, pathfinding, entity lists, packets) to Python as the `eXLib` module. The DLL source is **not** in this repo (it lives in sibling repo `../MetinPythonLib-WalkerPath`, upstream `ikevin127/MetinPythonLibV2-Rebuild`); `eXLib.mix` here is a committed binary. See `README.md` for the phase history and `docs/` for the RE workflow and a safety checklist.

## Build / test / run

There is no build, lint, or test suite. Code is plain Python 2.7 source executed by the game's embedded interpreter, so it cannot be run or imported standalone (it needs the live client, `eXLib`, and the client's `ui`/`chr`/`net`/`player` modules). Verification is in-game.

- Deploy to the client folder: `.\ubot-deploy.ps1 Status | Install | Remove` (supports `-WhatIf`, `-GameDir`, `-Items`, `-Force`). Default `GameDir` is `D:\Games\Gameforge\metin2\ro-RO`; deploys `eXLib.mix`, `init.py`, `OpenBot/`. Refuses to touch files while the client is running unless `-Force`; backs up existing files as `*.ubot-backup`.
- Iterate without restarting the client: type `/rah` in game chat to `reload()` the hot-reloadable modules, `/rah-ui` to also rebuild their windows in place (needed after `BuildWindow`/layout edits). `/shoprace` dumps nearby shop race ids.
- Syntax is Python 2 (`print` statements, `reload`, `exec` forms, tabs in some files) — don't modernize to Python 3. `.pyc` files are gitignored (some old ones are still tracked).

## Architecture

**Startup (`init.py`)** is one file executed *twice* by eXLib, phase-guarded by `sys._ubot_init_phase2`: call 1 at injection (bootstrap: discovers the client's renamed modules by probing `dir()` for known attributes, adds `OpenBot`, `OpenBot/lib`, `OpenBot/Modules` to `sys.path`), call 2 at first in-game (loader: imports modules, builds the hackbar `OpenBotHackbarDialog`, installs the chat-intercept hook for `/rah`). The DLL triggers it *after* the login→game transition, so init replays the game-phase callbacks once so `ActionBot`/`Data` initialize. Module-level names in both halves are intentionally shared (an `if/else` doesn't scope in Python).

**Client-module resolution** — the GF client obfuscates/renames its built-in modules (even prefixing attributes, e.g. `myth01734…`). `Modules/Hooks.py` and `init.py` locate `chr`, `net`, `player`, `chat`, `app`, etc. by scanning `sys.modules` for signature attributes (`HasArguments`). Use those resolved handles rather than `import chr`/`import net` in new code.

**`OpenBot/Modules/`** — one file per feature, mostly singletons exposing an `instance`:
- `OpenLib.py`: shared helpers (timers, phase, distance, player checks) and manual-intervention-stops-path detection; the common dependency for bots. The A* path helpers (`GoToPositionAvoidingObjects`, `StopMovement`) live in `Movement.py`, not `OpenLib`.
- `Hooks.py` / `Data.py`: game-window/phase hooks and shared state (`Data.*` serverInfo/mainVID/empireID is still partly unpopulated — see README "Stage 0").
- `Actions/` (`ActionBot`, `Action*`): scripted action sequences loaded from `Saves/Actions/*.action`, used by EnergyBot/NPC flows.
- Bots/UI: `ShopSearcher` (Trading Glass sweep), `Shopcreator` (ShopBot), `Pickup` (auto pickup: walks to the closest ground item the DLL selects and collects it with `eXLib.SendPickupItem`; standalone via the Pickup window/F8, or between fights via `AutoHunting`'s "Pickup" toggle; owns the `eXLib.ItemGrnd*` config and `Saves/pickup_filter.txt`), `EnergyBot`, `AutoHunting`, `StoneCompass`, `ChannelSwitcher`, `KeyBot`, `Skillbot`, `Settings`, etc. `UIComponents` wraps the client's `ui` widgets.
- Many other modules (DmgHacks, Telehack, Farming/Mining, Buffbot, Radar, AutoDungeon…) depend on the send-side packet layer, which is **disabled** in the DLL — treat them as dormant/not working unless the README's Phase 2 work has landed.

**Data**: `OpenBot/Maps/*.dat` (collision/walk data for pathfinding), `Saves/` (user configs, NPC maps, filters), `Images/` (TGA UI assets), `lib/` (vendored simplejson, decimal, numbers, struct for Py2.7).

## Conventions & gotchas

- **Hot-reload safety**: modules in `_RAH_RELOAD_LIST` (`init.py`: OpenLib, ShopSearcher, EnergyBot, AutoHunting, StoneCompass, Shopcreator, Pickup) must stay reload-safe — the module bottom rebinds the live singleton's class instead of creating a second instance/window. Preserve this pattern when editing them, and add new hot-reloadable modules to that list (and `/rah-ui`'s rebuild list if they have `_rebuildWindow`). The `/rah` hook lives in `init.py` precisely because it is never reloaded.
- **Positions**: use `eXLib.GetPixelPosition`, never `chr.GetPixelPosition` (returns NaN on 26.1.11 and silently breaks distance math). Guard against NaN.
- **No codecs in the client's Python**: `str.decode(...)` and `unicodedata` fail inside the client (codec modules aren't bundled), so don't decode/normalize item or chat text; compare raw characters (see `Pickup._nameMatches`). Also hold a reference to every `TextLine`/widget you create (e.g. in a `_keep` list) or the GC destroys it and the label vanishes.
- **Offsets/signatures are build-specific**: the DLL finds game functions by AOB signature, and the client updates often. A client patch can break eXLib without any Python change; fixes then belong in the DLL repo.
- Debug output is gated by per-module flags (`AH_DEBUG`, `EB_DEBUG`, `DEBUG` in ShopSearcher, `STATUS_DEBUG`, `PHASE1_DEBUG`, `MANUAL_STOP_DEBUG`); keep them `False` in committed code.
- Game automation violates the game's ToS; `docs/ISSUE-safety-concerns.md` documents the trust risks of the unreviewed `eXLib.mix` binary.
