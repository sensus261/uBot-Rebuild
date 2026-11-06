# uBot — WalkerPath build

A revived build of **uBot** (a minimal Metin2 bot that drives the `eXLib` python extension) for the **current GameForge Metin2 client** (`metin2client.exe`, 32-bit, packed / runtime-decrypted, protected by `psw_tnt`).

This folder is a working clone — the original `uBot` is kept untouched as a baseline. It pairs with the rebuilt DLL in [`../MetinPythonLib-WalkerPath`](../MetinPythonLib-WalkerPath), deployed here as `eXLib.mix`.

## How this was done

All of the reverse engineering and code surgery in this revival was performed by **Claude Opus 4.8** (`claude-opus-4-8`), running as an autonomous **Claude Code** agent (extended thinking / high reasoning effort), driving a live **CheatEngine MCP bridge** against the running game.

> The human operator does **not** do reverse engineering — a previous by-hand attempt to fix `eXLib` failed completely. Everything below (signature re-derivation, struct/offset discovery, build surgery, bot debugging) was worked out by the model from the running process + the leaked client source, step by step, and validated in-game.

**Tooling**
- CheatEngine MCP bridge: <https://github.com/miscusi-peek/cheatengine-mcp-bridge> — exposes CheatEngine to the model as tools (AOB scan, disassemble, read/write memory, evaluate Lua, enum modules) **without attaching a debugger**. The client's protection crashes on debugger/breakpoints, so only static reads + Lua were used.
- Visual Studio 2022 (MSVC **v142**) + Python 2.7 SDK — to rebuild the DLL.
- The leaked Metin2 `client-source` as a structural/protocol reference only (addresses don't transfer; structure does).

## RE techniques used

The client is recompiled often and ASLR'd, so nothing is hardcoded:
- **AOB (array-of-bytes) signatures** for every game function — stable across launches; addresses derived as RVAs. When a prologue drifted (e.g. a `/GS` stack cookie was added), the signature was re-derived from a fresh disassembly.
- **RVA rebasing** — the module base moves each launch (`0x280000` → `0x2F0000` → `0x530000` …); known globals were rebased by `base + (old_abs − old_base)` and re-validated.
- **Call-graph / this-pointer tracing** — followed `call` / `mov ecx,[global]` chains to locate singletons (character manager, network stream) and their methods.
- **Live struct discovery** — replicated the game's own resolution in CheatEngine Lua, then dumped float triplets / walked containers to find field offsets empirically (the instance position offset; the `std::map<VID, CInstanceBase*>` instance container).
- **Empirical validation** — every finding confirmed by moving the character / reading live state, never assumed.

## Phase 0 — Diagnosis

The pre-existing `eXLib.mix` crashed the client on entering the game world. Cause: it locates ~24 game functions via baked AOB signatures, and **13 of 24 were dead** on the current build (prologue drift). One dead signature (`PEEK`) caused a null-deref on load; the packet hooks dereferenced bad pointers on the in-game packet flood. So this was never "just the character-position constant" — it was wholesale signature/offset rot plus a load crash.

## Phase 1 — Walker + pathfinding revived (DONE)

Scope chosen with the operator: **walking + pathfinding + entity awareness** (not the full combat/packet set).

DLL side (see the other README): re-derived `MoveToDestPosition`, `App::Process` (init heartbeat) and `Peek`; fixed the character-position offset (`0x7C4` in source → **`0x7BC`** on this build; an interim `0x200` was wrong — it only worked on a PC-wrapper object, not the instances `eXLib` returns); disabled the crash-prone packet hooks; NULL-guarded all resolution so missing signatures no-op; stripped the unbuildable server-comms (curl/websocket) deps; rebuilt a clean 32-bit DLL.

Bot side (this folder):
- **Phase-replay** in `script.py` — the DLL now triggers `script.py` *after* the login→game transition, so uBot's own `net.SetPhaseWindow` hook misses the event and `ActionBot` never starts. We replay the game-phase callbacks once on load so ActionBot/Data/etc. initialize.
- **In-game diagnostics ticker** (`PHASE1_DEBUG = True` in `script.py`) — writes `Phase1Diag.txt` + a 1-line chat summary every ~8 s (positions, `InstancesList`, `FindPath`, bot states, a `serverInfo` dump). Set `PHASE1_DEBUG = False` to silence.
- **ChannelSwitcher fixed** — `GetCurrentServer()`/`GetCurrentChannel()` now read `net.GetServerInfo()` directly and match the name against `serverInfo.REGION_DICT` (auto-detect, no hardcoding) instead of a never-populated cache.
- **EnergyBot money gate** — replaced the silent pause with a throttled chat notice ("Needs at least N yang…").
- **FishingBot removed** entirely (file + `Data.py` timers).

**Working now:** player/entity coords, `InstancesList`/`IsDead`, `FindPath` + obstacle-avoiding navigation, `MoveToDestPosition` movement, ActionBot/Movement automation (EnergyBot walks to the NPC), ChannelSwitcher, KeyBot, zoom.

### Phase 1 Follow-Up Fixes

- **Map-warp crash fixed** (DLL side) — re-entering Python from the recv hook during the warp packet-flood crashed `python27.dll`; fixed by GIL-guarding eXLib's packet path. See the [`MetinPythonLib-WalkerPath`](../MetinPythonLib-WalkerPath) README.
- **EnergyBot → alchemist move** — `GetEnergyFromAlchemist` built its move with `GetPlayerEmpireFirstMap()`, which `KeyError`ed when `Data.empireID` was unset and otherwise used the wrong map, so the action threw and ActionBot stalled. Now it moves on the **current** map (the alchemist is always on it); `GetPlayerEmpireFirstMap/SecondMap` fall back to the current map instead of `KeyError`ing.
- **SearchBot "Move to Shop"** — was reading the vendor's position live at click time, which returns `(0,0,0)` once the owner is out of sight → character walked to the map origin (top-left). Position is now **captured at search time** (while the shop is open) and stored on the item; the move uses **A\* pathfinding** (`GoToPositionAvoidingObjects`, the EnergyBot pipeline) to route around walls, with a straight-line click-move fallback when the map has no collision data.
- **SearchBot results persist across areas** — re-searching no longer wipes the list; finds accumulate (refreshed per-shop on re-scan), so shops scanned before you moved out of range stay listed.
- **SearchBot item filter** — case-insensitive substring match (was case-sensitive, so partial matches often missed).
- **SearchBot price display** — shows the shop's real **Won + Yang** split in k/kk notation (e.g. `5Won 50kk`, `500kk`) instead of folding everything into yang.

### Auto pickup (added after Phase 1)

- **Auto pickup** — new `Pickup.py`. Walks to the closest ground item the DLL selects (filter, range, items-first and blocked-path rules are applied DLL-side via `eXLib.ItemGrnd*`) and collects it with `eXLib.SendPickupItem`. This needed a DLL fix: `SendPickupItem` used the dead raw send path and silently did nothing; it now calls the client's own `SendItemPickUpPacket` function (`SENDITEMPICKUP_FUNCTION`, see the DLL repo). Run it standalone (hackbar Pickup button / F8) or between fights via the **Pickup** toggle in the Auto-Hunt window. The Pickup window holds include/exclude filter (add by ID or name search), range and delay sliders and the items-first / ignore-blocked-path / avoid-players toggles. Per-item blacklist, `PHASE_GAME` only, NaN-guarded, no teleporting.

## Phase 2 — TODO (remaining functionality)

Most remaining bots are combat/skill/sync features that depend on the **send-side packet layer**, which is still off. Same methodology as Phase 1.

**Stage 0 — glue fixes**
- `Data._afterLoadPhase` doesn't populate `Data.*` (serverInfo / mainVID / empireID) — investigate + fix.
- `net.GetMainActorVID` doesn't exist on this client → replace with `player.GetMainCharacterIndex()`.
- `Hooks.GAME_WINDOW == 0` (missed `player.SetGameWindow` hook) → capture it.

**Stage 1 — re-derive the dead send/recv signatures**
- `SEND`, `SENDCHARACTERSTATE` (SendStatePacket), `SENDSHOOT`, `PYTHONPLAYER_SENDUSESKILL`, `LOCALTOGLOBAL`.
- Verify the matching ones call through without a hook (`SENDATTACK`, `SENDSEQUENCE`, `MOVETODIRECTION`, `GLOBALTOLOCAL`).
- Verify GF packet structs (`SSend_*`), then re-enable hooks one at a time with no-crash testing.

**Stage 2 — bring up features**
1. Combat / DmgHacks (attack, shoot, fly-target, block, state)
2. Skills — Skillbot / Buffbot (use-skill-by-slot)
3. Farming / Mining (dig recv callback + NPC click)
4. Movement extras — Telehack / speed-hack (state / sync / SetPixelPosition; the most anti-cheat-detectable)
5. Shops — ShopSearcher / Shopcreator (recv shop callback)
6. Remainder — Radar, AutoDungeon, Inventorymanager, Spambot

**Stage 3 — cleanup**
- Strip the dormant fishing exports from the DLL; decide on the phase-replay hack.

## Using this build
1. Load `eXLib.mix` into the running client with your usual injector (same path the original `eXLib` used).
2. Enter the world; the hackbar appears. With `PHASE1_DEBUG = True`, `Phase1Diag.txt` is written for visibility.

## ⚠️ Notes
Game automation / memory editing violates the game's Terms of Service and can get accounts banned — this is for educational/research use on your own account. The DLL embeds no anti-cheat evasion; it relies on the same injection path the original `eXLib` used.
