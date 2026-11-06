# AutoHunting: how "Skills" (auto skill) works

Source: `OpenBot/Modules/AutoHunting.py` (`_doSkills`, `resetSkillsUI`, `_refreshSkillDurations`).
Toggle: the **Skills** row in the Settings section (`autoSkill`). Per-skill toggles sit on each skill icon.

## Where it runs

`BotBase.OnUpdate` (0.2s gate) -> `Frame` -> `_tick`. In `_tick`, after the combat step:

```
if autoPotion: _doPotions()
if autoSkill:  _doSkills(mainVID); _refreshSkillDurations()
```

`_doSkills` itself is throttled to `SKILL_TICK` (0.4s) and returns immediately while mounted
(`player.IsMountingHorse()`).

## The skill set

`resetSkillsUI` builds `self.skillSet` from the character's class (`OpenLib.GetClassSkillIDs`).
Each entry holds: `id`, `slot`, `learned`, `isBuff`, the on/off `toggle`, the recast box `edit`,
`dur` and `lastCast`.

- **Buff** = a STANDING skill that is not an ATTACK skill (`_isBuffSkill`; static flag sets, client API
  only as fallback).
- **Offensive** = everything else.
- The set is rebuilt when the class/learned-skill signature changes (`_skillSignature`) or after a
  map change (`_skillsDirty`), at least 3s after the transition.

## Buffs (first)

A buff is **due and ready** when all of these hold:

1. learned, and its toggle is ON;
2. toggle auras (`OpenLib.SKILL_TOGGLE`) are cast **once** per Start/death/map change (`_toggleDone`);
   recasting would turn them OFF. Other buffs recast when `now - lastCast >= duration + 2s`, where
   `duration = skill.GetDuration(id, GetSkillCurrentEfficientPercentage(slot))` (falls back to the recast
   box, then to 20s);
3. not on cooldown (`player.IsSkillCoolTime(slot)`);
4. enough SP (`skill.GetSkillNeedSP`, or a 15% of max SP floor when that value is unusable). With too
   little SP the buff is skipped so the bot never stop-starts for a cast that cannot happen.

The first due-and-ready buff is cast only if:

- the char is **not mid-approach** to a target (unless the target is farther than `BUFF_FAR_DIST`,
  when `BUFF_WHILE_FAR_APPROACH` is on), and
- at least `BUFF_GCD` (3s) has passed since **any** skill cast (`_lastSkillCast`).

The cast: hold combat for 0.6s (`_castRestartAt`), stop the native engine and movement,
`player.ClickSkillSlot(slot)`, then **optimistically** set `lastCast = now` and return. One buff per tick.
If a gate fails the bot keeps attacking; the buff goes out in the next gap.

## Offensive skills (second)

Reached whenever no buff was cast this tick. Requires `_inMelee` (in attack range, bow-aware).

1. Pick the cast target: the committed hunt target if alive and within range, otherwise the nearest
   in-range mob (`_findNearestMob`). With `STICKY_TARGET` and a committed target not yet in range,
   return (never steal focus). No target in range -> return.
2. `player.SetTarget(target)` so need-target skills have a target.
3. For each learned, toggled-on, off-cooldown offensive skill: `player.ClickSkillSlot(slot)`, then stamp
   `lastCast` / `_lastOffCast` / `_lastSkillCast`.

## Timers and the clock

All stamps use `app.GetTime()`, which **jumps backward on map load**. After a teleport,
`onReenter` / `_rebaseTimers` zero the stamps, set `lastCast = -1e9` (buffs recast at once) and
`_lastOffCast = -1e9`. `BotBase` has its own Frame-gate stamp (`Data.time_BotBase_generalTimers`),
which is reset by `_resetPumpTimer`; see the teleport fix in the issue notes.

## Known weak spots (candidates, confirm with `AH_DEBUG` / `AH_TRACE` before changing)

- **Optimistic buff timer:** `lastCast` advances at click time. If the client drops the cast (inside another
  skill's animation, no SP at the moment, moving), that buff waits a whole `duration + 2s`.
- **Cooldown read:** `IsSkillCoolTime` is not reliable right after a cast, which is why there is no
  "did it land" check.
- **Mounted:** `_doSkills` returns early, so buffs lapse while mounted and are recast after dismount
  once their window has expired.
- **Far approach:** with `BUFF_WHILE_FAR_APPROACH` off, long chases starve buffs.
- **Stale clock after teleport:** covered by `_rebaseTimers` and the pump-timer reset above.

Debug output: set `AH_DEBUG` (chat) or `AH_TRACE` (`Saves/autohunt_trace.txt`) to log `[BUFF]`, `[BUFFCAST]`,
`[BUFFDUR]` and `[SK]` lines. Keep both `False` in committed code.
