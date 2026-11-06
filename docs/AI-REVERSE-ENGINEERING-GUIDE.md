# Reviving eXLib for the GameForge Metin2 client with an AI agent

> Saved reference (pasted by the user; written by the author of the rebuild repos).
> Original context: the guide describes how the outdated open-source MetinPythonLibV2
> (the `eXLib` that OpenBot needs) was rebuilt for the then-latest GameForge (GF) Metin2
> client (as of 20/06/26) without traditional manual reverse-engineering knowledge.

## The core concept

Instead of using Cheat Engine / IDA / Ghidra by hand, let a high-reasoning AI agent
interact directly with the live running game process, attached to Cheat Engine via MCP.

The AI reads memory, finds structures, generates AOB signatures, traces call graphs and
suggests/fixes code. The human only validates results in-game. This replaces the need for
deep reverse-engineering knowledge.

## Key tools

| Tool | Purpose | Link |
|------|---------|------|
| Claude Opus 4.8 (or another high-reasoning LLM with tool calling) | Autonomous reverse-engineering agent | Claude Code CLI |
| Cheat Engine MCP Bridge | Lets the AI drive Cheat Engine through function calls (memory reads, AOB scanning, Lua execution) | github.com/miscusi-peek/cheatengine-mcp-bridge |
| Outdated Metin2 client source | Reference for structures/classes (`CInstanceBase`, ...) and network protocol | github.com/ikevin127/metin2-client-source |
| Visual Studio 2022 + Detours | Building the injectable DLL library | |

**Important:** the method uses static memory reads + Lua only (no debugger attachment),
because the client's protection crashes on Cheat Engine breakpoint attachment.

## High-level workflow (proven on the GF client)

1. **Diagnosis**
   - Test all existing AOB signatures against the live client.
   - Identify which are dead (here: 13 of 24 were outdated).
2. **AI-driven analysis**
   - AI explores the live process (this-pointers, vtables, call graphs).
   - Re-derives fresh AOB signatures where needed.
   - Finds correct struct offsets (example: character position moved from the expected
     `0x7C4` to the real `0x7BC` in `CInstanceBase`).
   - Handles ASLR by working with RVAs.
3. **Code adjustments**
   - Update offsets and signatures in `defines.h` / `Offsets.h`.
   - Add NULL guards so dead signatures don't crash the DLL.
   - Temporarily strip unused parts (server communication code).
   - Fix threading issues (especially the Python GIL when re-enabling packet hooks).
4. **Build & test**
   - Compile with MSBuild (Release | Win32 | v142 toolset).
   - Deploy as `eXLib.mix`, which **auto-injects** (or use the `.dll` with an injector).
   - Validate live in-game (position reading, pathfinding, ...).
5. **Iterative improvement**
   - Re-enable features one by one (e.g. the `CheckPacket` hook).
   - Fix crashes (GIL hardening + error clearing was required).

## Why this works for non-reverse-engineers

- The AI does the disassembly interpretation and pattern finding.
- You only need to give clear goals, apply the suggested code changes, and test in-game.
- No manual signature scanning or deep ASM knowledge required.

## Limitations & notes

- The method can be reused for new game updates / outdated addresses whenever the client
  is rebuilt (new game version release).
- Educational / research use only. Automating gameplay violates Metin2's ToS.
- No anti-cheat bypasses were added; it uses the same injection method as the original library.

## Resources

- Reference library rebuild: github.com/ikevin127/MetinPythonLibV2-Rebuild
- Detailed rebuild log: "WalkerPath Revival" section (see this repo's `README.md`)
- Cheat Engine MCP bridge: github.com/miscusi-peek/cheatengine-mcp-bridge
- Client source reference: github.com/ikevin127/metin2-client-source

---

## Project notes (added later)

- Deployment: `eXLib.mix` is the auto-injecting form (no separate injector needed); the
  plain `.dll` needs an injector. `ubot-deploy.ps1` copies `eXLib.mix`, `init.py` and
  `OpenBot/` into the game folder.
- The DLL's source is `MetinPythonLibV2-Rebuild` (not an injector). Pattern tooling lives in
  its `PatternScanner/`, `patterns_aob.json`, `parse_patterns.py`, `verify_patterns.py`.
- Version caveat: this uBot build targets GF client **26.1.11**. A newer client (e.g.
  26.2.10) can break signatures/offsets again, which means re-deriving them in the DLL repo.
