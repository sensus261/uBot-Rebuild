# Routing tables

Used by the analyze, review, changelog and docs commands. Read once per run.

## Area tags

| Tag | Paths |
|---|---|
| `[BOOT]` | `init.py`, `OpenBot/__init__.py` |
| `[HOOKS]` | `OpenBot/Modules/Hooks.py`, `Data.py`, `OpenThreads.py`, `OpenLog.py` |
| `[MOVE]` | `OpenBot/Modules/OpenLib.py`, `Movement.py`, `MapManager.py`, `OpenBot/Maps/*.dat` |
| `[ACTIONS]` | `OpenBot/Modules/Actions/*`, `OpenBot/Saves/Actions/*.action`, `NPCInteraction.py` |
| `[HUNT]` | `AutoHunting.py`, `Levelbot.py`, `FarmingBot.py`, `Skillbot.py`, `Buffbot.py`, `KeyBot.py`, `AutoDungeon.py`, `StoneCompass.py`, `Radar.py` |
| `[SHOP]` | `ShopSearcher.py`, `Shopcreator.py`, `Inventorymanager.py` |
| `[ENERGY]` | `EnergyBot.py`, `ChannelSwitcher.py` |
| `[UI]` | `UIComponents.py`, `Settings.py`, `OpenBot/Images/*`, hackbar code in `init.py` |
| `[DLL]` | `eXLib.mix` (prebuilt binary; source lives in `../MetinPythonLib-WalkerPath`) |
| `[DEPLOY]` | `ubot-deploy.ps1` |
| `[DORMANT]` | `DmgHacks.py`, `Telehack.py`, `Spambot.py`, `PythonManager.py`: depend on the disabled send-side packet layer |
| `[DOCS]` | `README.md`, `RELEASE_NOTES.md`, `CLAUDE.md`, `docs/*`, `.claude/*` |
| `[LIB]` | `OpenBot/lib/*` (vendored simplejson, decimal, numbers, struct) |

A file in several areas gets several tags. Compiled `*.pyc` files are noise (see the skip list).

## Doc mapping

| Changed area | Read / update |
|---|---|
| `[BOOT]` | `CLAUDE.md` §Architecture (two-phase `init.py`), `README.md` phase history |
| `[DLL]`, `[DORMANT]`, anything calling `eXLib.*` | `CLAUDE.md` §Architecture, `README.md` Phase 2 notes, `docs/ISSUE-safety-concerns.md` |
| New or changed RE workflow, signatures | `docs/AI-REVERSE-ENGINEERING-GUIDE.md` |
| `[DEPLOY]` | `CLAUDE.md` §Build / test / run |
| `[HOOKS]`, `[MOVE]`, `[ACTIONS]`, `[HUNT]`, `[SHOP]`, `[ENERGY]`, `[UI]` | `CLAUDE.md` §Architecture + §Conventions; the feature's entry in `README.md` / `RELEASE_NOTES.md` |
| Hot-reload list or `/rah` behavior | `CLAUDE.md` §Conventions (Hot-reload safety) |

## Sync pairs

A change on one side needs a look at the other.

| If this changes | Check this |
|---|---|
| A module is added to / removed from `_RAH_RELOAD_LIST` in `init.py` | That module keeps the reload-safe bottom (rebinds the live singleton's class), and `/rah-ui` rebuild list if it has `_rebuildWindow`; `CLAUDE.md` §Conventions list |
| A module gains `BuildWindow` / layout changes | `/rah-ui` rebuild list in `init.py` |
| A new module is added under `OpenBot/Modules/` | `init.py` loader imports, `CLAUDE.md` §Architecture list, area table above |
| A debug flag (`AH_DEBUG`, `EB_DEBUG`, `DEBUG`, `STATUS_DEBUG`, `PHASE1_DEBUG`, `MANUAL_STOP_DEBUG`) | Must be `False` in committed code |
| An `eXLib.*` call is added or its signature assumed | The DLL repo actually exports it for the targeted client build; `README.md` |
| `ubot-deploy.ps1` default items or paths | `CLAUDE.md` §Build / test / run, `README.md` |
| A user-visible feature, fix or version | `RELEASE_NOTES.md` |
| `OpenBot/Saves/*` schema (config keys, `.action` format) | The loader in the owning module and any shipped sample files |

## Skip list pointers

See `digest-discovery.md` §Skip list.
